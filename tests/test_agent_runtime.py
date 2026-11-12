from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from humanity_os.agent_runtime import AgentRuntimeStore
from humanity_os.app import create_app
from humanity_os.memory import MemoryStore
from humanity_os.store import KnowledgeStore


def _client(tmp_path, authenticated=False):
    app = create_app(
        str(tmp_path / "workspace.sqlite3"),
        allow_unauthenticated_local=not authenticated,
    )
    return app, TestClient(app, client=("127.0.0.1", 50000))


def test_profiles_expose_only_declared_local_capabilities(tmp_path):
    app, client = _client(tmp_path)
    profiles = {item["id"]: item for item in client.get("/v1/agents").json()["items"]}
    assert set(profiles) == {"researcher", "curator"}
    researcher_tools = {
        item["name"] for item in client.get(
            "/v1/agents/tools", params={"agent_id": "researcher"}
        ).json()["items"]
    }
    curator_tools = {
        item["name"] for item in client.get(
            "/v1/agents/tools", params={"agent_id": "curator"}
        ).json()["items"]
    }
    assert "memory.propose" not in researcher_tools
    assert "memory.propose" in curator_tools
    assert "memory.approve" not in curator_tools
    assert client.get("/v1/agents/tools", params={"agent_id": "missing"}).status_code == 404
    assert app.state.agent_runtime is not None


def test_researcher_invokes_bounded_local_search_and_records_minimal_audit(tmp_path):
    app, client = _client(tmp_path)
    created = client.post(
        "/v1/knowledge",
        json={
            "kind": "observation",
            "title": "Local fact",
            "content": "The owner keeps source data local.",
            "visibility": "private",
        },
    ).json()
    response = client.post(
        "/v1/agents/researcher/invoke",
        json={"tool_name": "knowledge.search", "arguments": {"query": "source data"}},
    )
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert response.json()["result"][0]["id"] == created["id"]
    run = app.state.agent_runtime.store.list_runs()[0]
    assert run["status"] == "completed"
    assert run["input_digest"]
    assert run["result_digest"]
    events = app.state.agent_runtime.store.list_events(run_id)
    assert [event["event_type"] for event in events] == [
        "tool_invocation_started",
        "tool_invocation_completed",
    ]
    serialized_audit = json.dumps({"run": run, "events": events})
    assert "The owner keeps source data local." not in serialized_audit
    assert "source data" not in serialized_audit


def test_agent_runtime_denies_ungranted_tools_and_unknown_agents(tmp_path):
    _, client = _client(tmp_path)
    denied = client.post(
        "/v1/agents/researcher/invoke",
        json={
            "tool_name": "memory.propose",
            "arguments": {
                "title": "Forbidden",
                "content": "No implicit writes.",
                "rationale": "Policy test.",
            },
        },
    )
    assert denied.status_code == 403
    assert client.post(
        "/v1/agents/unknown/invoke",
        json={"tool_name": "documents.search", "arguments": {"query": "private"}},
    ).status_code == 404


def test_curator_can_create_pending_memory_but_never_approve_it(tmp_path):
    _, client = _client(tmp_path)
    result = client.post(
        "/v1/agents/curator/invoke",
        json={
            "tool_name": "memory.propose",
            "arguments": {
                "title": "Owner review required",
                "content": "This proposal is not durable memory.",
                "rationale": "The curator can only propose.",
            },
        },
    )
    assert result.status_code == 201
    proposal_id = result.json()["result"]["proposal_id"]
    assert result.json()["result"]["status"] == "pending_review"
    assert result.json()["result"]["requires_owner_approval"] is True
    assert client.get("/v1/memories").json()["items"] == []
    assert client.get(f"/v1/memory/proposals/{proposal_id}").json()["status"] == "pending_review"
    assert "memory.approve" not in {
        item["name"] for item in client.get(
            "/v1/agents/tools", params={"agent_id": "curator"}
        ).json()["items"]
    }


def test_invalid_agent_tool_arguments_are_bounded_and_audited(tmp_path):
    app, client = _client(tmp_path)
    response = client.post(
        "/v1/agents/researcher/invoke",
        json={
            "tool_name": "documents.search",
            "arguments": {"query": "x", "unlisted": "must be rejected"},
        },
    )
    assert response.status_code == 422
    run = app.state.agent_runtime.store.list_runs()[0]
    assert run["status"] == "failed"
    assert run["error_code"] == "ValidationError"
    too_large = client.post(
        "/v1/agents/researcher/invoke",
        json={"tool_name": "documents.search", "arguments": {"query": "x" * 21_000}},
    )
    assert too_large.status_code == 422


def test_agent_runtime_requires_authentication(tmp_path):
    _, client = _client(tmp_path, authenticated=True)
    assert client.get("/v1/agents").status_code == 401
    assert client.post(
        "/v1/agents/researcher/invoke",
        json={"tool_name": "documents.search", "arguments": {"query": "private"}},
    ).status_code == 401


def test_agent_events_are_append_only_and_interrupted_runs_are_recovered(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    store = AgentRuntimeStore(database)
    run_id = store.start_run("researcher", "documents.search", "a" * 64)
    with sqlite3.connect(database) as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "UPDATE agent_events SET event_type = 'forged' WHERE run_id = ?",
            (run_id,),
        )

    recovered = AgentRuntimeStore(database)
    run = recovered.list_runs()[0]
    assert run["status"] == "failed"
    assert run["error_code"] == "interrupted"
    assert [event["event_type"] for event in recovered.list_events(run_id)] == [
        "tool_invocation_started",
        "tool_invocation_failed",
    ]


def test_agent_run_events_are_included_in_portable_export(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    app = create_app(str(database), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Portable", "content": "Agent history is portable."},
    )
    invocation = client.post(
        "/v1/agents/researcher/invoke",
        json={"tool_name": "knowledge.search", "arguments": {"query": "portable"}},
    )
    assert invocation.status_code == 201
    exported = KnowledgeStore(database).export_workspace()
    assert exported["schema_version"] == "1.3.0"
    assert len(exported["tables"]["agent_runs"]) == 1
    assert len(exported["tables"]["agent_events"]) == 2

    export_path = tmp_path / "agents.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")
    target = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")
    restored = AgentRuntimeStore(target)
    assert restored.list_runs()[0]["id"] == invocation.json()["run_id"]
    assert len(restored.list_events(invocation.json()["run_id"])) == 2
