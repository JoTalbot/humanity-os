from __future__ import annotations

import json

from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.model_gateway import ProviderGeneration


class TransientTestProvider:
    provider_id = "test-only"
    model_id = "e2e-fixture"

    async def generate(self, request):
        assert "Project records stay on the local workspace." in request.prompt
        return ProviderGeneration(output="The records stay local [S1].")


def test_humanity_one_complete_local_owner_journey_and_portability(tmp_path):
    database = str(tmp_path / "humanity.sqlite3")
    password = "a long secure owner password"
    app = create_app(database)
    app.state.auth_store.set_owner_password(password)
    client = TestClient(app, client=("127.0.0.1", 50000))

    login = client.post("/auth/login", json={"password": password})
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    session_cookie = client.cookies.get("humanity_session")
    assert session_cookie

    headers = {"X-CSRF-Token": csrf}
    note = client.post(
        "/v1/knowledge",
        json={
            "kind": "observation",
            "title": "Workspace operating rule",
            "content": "Keep project records local and source-linked.",
            "visibility": "private",
        },
        headers=headers,
    )
    assert note.status_code == 201

    document = client.post(
        "/v1/documents",
        json={
            "filename": "project-records.md",
            "content": "Project records stay on the local workspace. Sources remain traceable.",
        },
        headers=headers,
    )
    assert document.status_code == 201
    doc = document.json()
    chunk = doc["chunks"][0]

    context = client.post(
        "/v1/documents/context",
        json={"query": "project records local", "passage_limit": 3, "max_context_chars": 1024},
        headers=headers,
    )
    assert context.status_code == 200
    assert context.json()["processing"]["model_called"] is False
    assert context.json()["passages"][0]["chunk_id"] == chunk["id"]

    proposal = client.post(
        "/v1/memory/proposals",
        json={
            "title": "Local data policy",
            "content": "Project records stay on the local workspace.",
            "rationale": "Owner-selected operating rule.",
            "source_document_id": doc["id"],
            "source_chunk_id": chunk["id"],
        },
        headers=headers,
    )
    assert proposal.status_code == 201
    proposal_id = proposal.json()["id"]
    assert proposal.json()["status"] == "pending_review"
    assert client.get("/v1/memories").json()["items"] == []

    approved = client.post(
        f"/v1/memory/proposals/{proposal_id}/approve",
        headers=headers,
    )
    assert approved.status_code == 201
    memory_id = approved.json()["id"]
    assert approved.json()["source_chunk_id"] == chunk["id"]
    assert client.post(f"/v1/memories/{memory_id}/archive", headers=headers).json()["status"] == "archived"
    assert client.post(f"/v1/memories/{memory_id}/restore", headers=headers).json()["status"] == "active"

    # Explicit consent alone must not activate a provider or create outbound traffic.
    unavailable = client.post(
        "/v1/documents/answer",
        json={"query": "project records local", "allow_provider_processing": True},
        headers=headers,
    )
    assert unavailable.status_code == 503
    assert app.state.model_gateway.provider is None

    # A test-only injected provider demonstrates the consented path without any real integration.
    test_app = create_app(database, model_provider=TransientTestProvider())
    test_client = TestClient(test_app, client=("127.0.0.1", 50001))
    test_login = test_client.post("/auth/login", json={"password": password})
    test_headers = {"X-CSRF-Token": test_login.json()["csrf_token"]}
    answer = test_client.post(
        "/v1/documents/answer",
        json={"query": "project records local", "allow_provider_processing": True},
        headers=test_headers,
    )
    assert answer.status_code == 200
    assert answer.json()["answer"] == "The records stay local [S1]."
    assert answer.json()["citations"][0]["chunk_id"] == chunk["id"]

    exported_response = test_client.get("/v1/workspace/export")
    assert exported_response.status_code == 200
    exported = exported_response.json()
    serialized = json.dumps(exported, ensure_ascii=False)
    assert exported["schema_version"] == "1.2.0"
    assert len(exported["tables"]["knowledge"]) == 1
    assert len(exported["tables"]["documents"]) == 1
    assert len(exported["tables"]["memory_items"]) == 1
    assert "The records stay local [S1]." not in serialized
    assert password not in serialized
    assert csrf not in serialized
    assert session_cookie not in serialized
