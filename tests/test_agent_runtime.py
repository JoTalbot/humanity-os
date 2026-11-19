from __future__ import annotations

import json
import multiprocessing
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from humanity_os.agent_runtime import AgentRunLeaseLost, AgentRuntimeStore
from humanity_os.app import create_app
from humanity_os.store import KnowledgeStore


def _recover_run_in_process(database_path, worker_id, recovery_at, barrier, results):
    store = AgentRuntimeStore(
        database_path, worker_id=worker_id, lease_duration_seconds=30
    )
    barrier.wait(timeout=10)
    results.put(store.recover_expired_runs(now=datetime.fromisoformat(recovery_at)))


def _start_run_with_inherited_store(store, results):
    run_id = store.start_run(
        "researcher", "documents.search", "c" * 64, now=datetime.now(UTC)
    )
    results.put((store.worker_id, run_id))


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
    app, client = _client(tmp_path)
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
    run = app.state.agent_runtime.store.list_runs()[0]
    assert run["status"] == "completed"
    assert [event["event_type"] for event in app.state.agent_runtime.store.list_events(run["id"])] == [
        "tool_invocation_started",
        "tool_invocation_completed",
    ]
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


def test_agent_events_are_append_only_and_live_runs_survive_second_worker_startup(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    started_at = datetime.now(UTC)
    owner = AgentRuntimeStore(database, worker_id="worker-a", lease_duration_seconds=30)
    run_id = owner.start_run(
        "researcher", "documents.search", "a" * 64, now=started_at
    )
    with sqlite3.connect(database) as connection, pytest.raises(
        sqlite3.IntegrityError, match="append-only"
    ):
        connection.execute(
            "UPDATE agent_events SET event_type = 'forged' WHERE run_id = ?",
            (run_id,),
        )

    observer = AgentRuntimeStore(database, worker_id="worker-b", lease_duration_seconds=30)
    run = observer.list_runs()[0]
    assert run["status"] == "running"
    assert run["worker_id"] == "worker-a"
    assert run["lease_expires_at"] == (started_at + timedelta(seconds=30)).isoformat()
    assert observer.recover_expired_runs(now=started_at + timedelta(seconds=29)) == 0
    assert observer.list_runs(now=started_at + timedelta(seconds=31))[0]["status"] == "failed"
    assert observer.recover_expired_runs(now=started_at + timedelta(seconds=32)) == 0
    with pytest.raises(RuntimeError, match="lease"):
        owner.finish_run(run_id, result_digest="b" * 64, now=started_at + timedelta(seconds=32))

    recovered = observer.list_runs()[0]
    assert recovered["status"] == "failed"
    assert recovered["error_code"] == "interrupted"
    assert [event["event_type"] for event in observer.list_events(run_id)] == [
        "tool_invocation_started",
        "tool_invocation_failed",
    ]


def test_worker_identity_is_regenerated_after_process_fork(tmp_path, monkeypatch):
    store = AgentRuntimeStore(
        tmp_path / "workspace.sqlite3", worker_id="parent-worker", lease_duration_seconds=30
    )
    parent_pid = store._process_id

    monkeypatch.setattr("humanity_os.agent_runtime.os.getpid", lambda: parent_pid + 1)
    run_id = store.start_run(
        "researcher", "documents.search", "a" * 64, now=datetime.now(UTC)
    )

    run = store.list_runs()[0]
    assert store.worker_id != "parent-worker"
    assert run["worker_id"] == store.worker_id
    assert run["id"] == run_id


def test_expired_run_recovery_is_exactly_once_across_processes(tmp_path):
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("fork-based SQLite concurrency test requires a POSIX process model")
    context = multiprocessing.get_context("fork")
    database = tmp_path / "workspace.sqlite3"
    owner = AgentRuntimeStore(
        database, worker_id="owner", lease_duration_seconds=30
    )
    started_at = datetime.now(UTC) + timedelta(seconds=60)
    run_id = owner.start_run(
        "researcher", "documents.search", "a" * 64, now=started_at
    )
    recovery_at = started_at + timedelta(seconds=31)
    barrier = context.Barrier(2)
    results = context.Queue()
    workers = [
        context.Process(
            target=_recover_run_in_process,
            args=(str(database), f"worker-{index}", recovery_at.isoformat(), barrier, results),
        )
        for index in range(2)
    ]

    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert worker.exitcode == 0

    recovered_counts = [results.get(timeout=2), results.get(timeout=2)]
    assert sum(recovered_counts) == 1
    assert owner.list_runs(now=recovery_at)[0]["status"] == "failed"
    assert len(owner.list_events(run_id)) == 2


def test_forked_process_does_not_reuse_parent_worker_identity(tmp_path):
    if "fork" not in multiprocessing.get_all_start_methods():
        pytest.skip("fork identity test requires a POSIX process model")
    context = multiprocessing.get_context("fork")
    database = tmp_path / "workspace.sqlite3"
    parent = AgentRuntimeStore(
        database, worker_id="parent-worker", lease_duration_seconds=30
    )
    results = context.Queue()
    worker = context.Process(
        target=_start_run_with_inherited_store, args=(parent, results)
    )

    worker.start()
    worker.join(timeout=15)
    assert worker.exitcode == 0
    child_worker_id, run_id = results.get(timeout=2)

    assert child_worker_id != "parent-worker"
    assert parent.list_runs()[0]["id"] == run_id
    assert parent.list_runs()[0]["worker_id"] == child_worker_id
    with pytest.raises(RuntimeError, match="lease"):
        parent.finish_run(run_id, result_digest="d" * 64)


def test_agent_run_lease_can_be_renewed_before_expiry(tmp_path):
    started_at = datetime.now(UTC)
    store = AgentRuntimeStore(
        tmp_path / "workspace.sqlite3", worker_id="worker-a", lease_duration_seconds=30
    )
    run_id = store.start_run(
        "researcher", "documents.search", "a" * 64, now=started_at
    )

    store.renew_run_lease(run_id, now=started_at + timedelta(seconds=20))

    run = store.list_runs()[0]
    assert run["lease_expires_at"] == (started_at + timedelta(seconds=50)).isoformat()
    assert store.recover_expired_runs(now=started_at + timedelta(seconds=31)) == 0


def test_expired_run_is_recovered_exactly_once_by_concurrent_workers(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    now = datetime.now(UTC)
    worker_a = AgentRuntimeStore(database, worker_id="worker-a", lease_duration_seconds=30)
    worker_b = AgentRuntimeStore(database, worker_id="worker-b", lease_duration_seconds=30)
    run_id = worker_a.start_run(
        "researcher",
        "documents.search",
        "a" * 64,
        now=now - timedelta(seconds=60),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda store: store.recover_expired_runs(now=now),
                (worker_a, worker_b),
            )
        )

    assert sum(results) == 1
    assert worker_a.list_runs()[0]["status"] == "failed"
    assert len(worker_a.list_events(run_id)) == 2


def test_legacy_running_rows_without_lease_columns_are_migrated_and_recovered(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    started_at = datetime.now(UTC).isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE agent_runs (
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, tool_name TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                input_digest TEXT NOT NULL, result_digest TEXT, error_code TEXT
            )"""
        )
        connection.execute(
            """CREATE TABLE agent_events (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, details TEXT NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO agent_runs(
                id, agent_id, tool_name, status, started_at, input_digest
            ) VALUES ('legacy-run', 'researcher', 'documents.search', 'running', ?, ?)""",
            (started_at, "a" * 64),
        )
        connection.execute(
            """INSERT INTO agent_events(id, run_id, event_type, occurred_at, details)
            VALUES ('legacy-event', 'legacy-run', 'tool_invocation_started', ?, ?)""",
            (started_at, json.dumps({"agent_id": "researcher", "tool_name": "documents.search"})),
        )

    migrated = AgentRuntimeStore(database, worker_id="worker-new")
    run = migrated.list_runs()[0]
    assert "worker_id" in run
    assert "lease_expires_at" in run
    assert run["status"] == "failed"
    assert run["error_code"] == "interrupted"


def test_agent_runtime_heartbeat_preserves_a_tool_call_longer_than_its_lease(tmp_path):
    app, _ = _client(tmp_path)
    runtime = app.state.agent_runtime
    runtime.store.lease_duration_seconds = 0.3
    runtime.store.heartbeat_interval_seconds = 0.05
    entered = threading.Event()
    release = threading.Event()
    original_search = runtime.documents.search
    def blocked_search(query, limit=10):
        entered.set()
        if not release.wait(timeout=3):
            raise TimeoutError("test did not release the blocked tool")
        return original_search(query, limit=limit)

    runtime.documents.search = blocked_search

    with ThreadPoolExecutor(max_workers=1) as executor:
        invocation = executor.submit(
            runtime.invoke, "researcher", "documents.search", {"query": "local"}
        )
        assert entered.wait(timeout=2)
        time.sleep(0.45)

        observer = AgentRuntimeStore(
            tmp_path / "workspace.sqlite3", worker_id="observer", lease_duration_seconds=30
        )
        assert observer.list_runs()[0]["status"] == "running"
        release.set()
        result = invocation.result(timeout=3)

    assert result["run_id"] == observer.list_runs()[0]["id"]
    assert observer.list_runs()[0]["status"] == "completed"


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
    assert "worker_id" not in exported["tables"]["agent_runs"][0]
    assert "lease_expires_at" not in exported["tables"]["agent_runs"][0]

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


def test_imported_running_agent_run_is_recovered_without_a_live_owner_lease(tmp_path):
    source = tmp_path / "source.sqlite3"
    source_store = AgentRuntimeStore(
        source, worker_id="source-worker", lease_duration_seconds=30
    )
    run_id = source_store.start_run(
        "researcher",
        "documents.search",
        "a" * 64,
        now=datetime.now(UTC),
    )
    export_path = tmp_path / "running-agent.json"
    export_path.write_text(
        json.dumps(KnowledgeStore(source).export_workspace()), encoding="utf-8"
    )

    target = tmp_path / "target.sqlite3"
    app = create_app(str(target), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")

    response = client.get("/v1/agents/runs")
    imported = next(item for item in response.json()["items"] if item["id"] == run_id)
    assert imported["status"] == "failed"
    assert imported["error_code"] == "interrupted"
    assert [
        event["event_type"]
        for event in app.state.agent_runtime.store.list_events(run_id)
    ] == ["tool_invocation_started", "tool_invocation_failed"]


def test_agent_events_are_bounded_and_run_completion_is_single_use(tmp_path):
    store = AgentRuntimeStore(tmp_path / "agent-audit.sqlite3")
    run_id = store.start_run("researcher", "knowledge.search", "a" * 64)
    store.finish_run(run_id, result_digest="b" * 64)

    with pytest.raises(ValueError, match="already finished"):
        store.finish_run(run_id, result_digest="c" * 64)

    assert len(store.list_events(run_id=run_id, limit=1)) == 1
    assert len(store.list_events(run_id=run_id, limit=2)) == 2
    with pytest.raises(ValueError, match="event limit"):
        store.list_events(run_id=run_id, limit=101)



def test_agent_api_returns_conflict_when_run_lease_is_lost(tmp_path):
    app, client = _client(tmp_path)
    runtime = app.state.agent_runtime

    def lose_lease(*args, **kwargs):
        raise AgentRunLeaseLost("lease expired")

    runtime.store.finish_run = lose_lease
    response = client.post(
        "/v1/agents/researcher/invoke",
        json={"tool_name": "documents.search", "arguments": {"query": "local"}},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Agent run lease was lost; the result was not accepted"



def test_curator_memory_proposal_event_identifies_agent_actor(tmp_path):
    app, client = _client(tmp_path)
    response = client.post(
        "/v1/agents/curator/invoke",
        json={
            "tool_name": "memory.propose",
            "arguments": {
                "title": "Attributed proposal",
                "content": "The actor must be the curator.",
                "rationale": "Audit provenance regression.",
            },
        },
    )
    assert response.status_code == 201
    proposal_id = response.json()["result"]["proposal_id"]
    events = app.state.agent_runtime.memory.list_events(proposal_id=proposal_id)
    assert len(events) == 1
    assert events[0]["event_type"] == "proposal_created"
    assert events[0]["actor"] == "curator"


def test_curator_does_not_create_proposal_after_lease_expiry(tmp_path):
    app, _ = _client(tmp_path)
    runtime = app.state.agent_runtime
    runtime.store.lease_duration_seconds = 0.01
    runtime.store.heartbeat_interval_seconds = 60
    original_start_run = runtime.store.start_run

    def start_expired_run(agent_id, tool_name, input_digest, *, now=None):
        return original_start_run(
            agent_id,
            tool_name,
            input_digest,
            now=datetime.now(UTC) - timedelta(seconds=2),
        )

    runtime.store.start_run = start_expired_run

    with pytest.raises(AgentRunLeaseLost, match="lease"):
        runtime.invoke(
            "curator",
            "memory.propose",
            {
                "title": "Must not persist",
                "content": "Lease already expired.",
                "rationale": "Side-effect fencing regression.",
            },
        )

    assert runtime.memory.list_proposals() == []


def test_concurrent_worker_startup_serializes_legacy_lease_migration(tmp_path):
    database = tmp_path / "legacy-concurrent.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE agent_runs (
                id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, tool_name TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
                input_digest TEXT NOT NULL, result_digest TEXT, error_code TEXT
            )"""
        )
        connection.execute(
            """CREATE TABLE agent_events (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, details TEXT NOT NULL
            )"""
        )

    barrier = threading.Barrier(2)

    def initialize(worker_id):
        barrier.wait(timeout=5)
        return AgentRuntimeStore(database, worker_id=worker_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        stores = list(executor.map(initialize, ("worker-a", "worker-b")))

    with sqlite3.connect(database) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")
        }
    assert {"worker_id", "lease_expires_at"} <= columns
    assert all(store.list_runs() == [] for store in stores)



def test_curator_proposal_and_run_completion_roll_back_together_on_lease_loss(tmp_path):
    app, _ = _client(tmp_path)
    runtime = app.state.agent_runtime

    def lose_lease_before_terminal_commit(*args, **kwargs):
        raise AgentRunLeaseLost("lease expired before terminal commit")

    runtime.store.finish_run = lose_lease_before_terminal_commit

    with pytest.raises(AgentRunLeaseLost, match="lease"):
        runtime.invoke(
            "curator",
            "memory.propose",
            {
                "title": "Atomic proposal",
                "content": "This must roll back with the run.",
                "rationale": "Verify one-transaction side-effect fencing.",
            },
        )

    assert runtime.memory.list_proposals() == []
    run = runtime.store.list_runs()[0]
    assert run["status"] == "running"
    assert [event["event_type"] for event in runtime.store.list_events(run["id"])] == [
        "tool_invocation_started"
    ]

    recovered_at = datetime.now(UTC) + timedelta(seconds=120)
    assert runtime.store.recover_expired_runs(now=recovered_at) == 1
    recovered = runtime.store.list_runs(now=recovered_at)[0]
    assert recovered["status"] == "failed"
    assert recovered["error_code"] == "interrupted"
    assert [event["event_type"] for event in runtime.store.list_events(run["id"])] == [
        "tool_invocation_started",
        "tool_invocation_failed",
    ]


def test_expired_worker_cannot_renew_lease_or_resurrect_run(tmp_path):
    database = tmp_path / "expired-lease.sqlite3"
    started_at = datetime.now(UTC)
    owner = AgentRuntimeStore(
        database, worker_id="worker-owner", lease_duration_seconds=30
    )
    observer = AgentRuntimeStore(
        database, worker_id="worker-observer", lease_duration_seconds=30
    )
    run_id = owner.start_run(
        "researcher",
        "documents.search",
        "a" * 64,
        now=started_at,
    )
    expired_at = started_at + timedelta(seconds=31)

    with pytest.raises(AgentRunLeaseLost, match="lease"):
        owner.renew_run_lease(run_id, now=expired_at)

    assert observer.recover_expired_runs(now=expired_at) == 1
    recovered = observer.list_runs(now=expired_at)[0]
    assert recovered["status"] == "failed"
    assert recovered["error_code"] == "interrupted"
    with pytest.raises(AgentRunLeaseLost, match="lease"):
        owner.renew_run_lease(run_id, now=expired_at + timedelta(seconds=1))
    assert len(observer.list_events(run_id)) == 2


@pytest.mark.parametrize("lease_duration", [0, -1, float("nan"), float("inf"), -float("inf"), True])
def test_agent_runtime_rejects_non_finite_or_non_positive_lease_duration(
    tmp_path, lease_duration
):
    with pytest.raises(ValueError, match="finite positive"):
        AgentRuntimeStore(
            tmp_path / "invalid-lease.sqlite3",
            lease_duration_seconds=lease_duration,
        )
