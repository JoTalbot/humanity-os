from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.documents import DocumentStore
from humanity_os.memory import MemoryStore
from humanity_os.store import KnowledgeStore


def test_proposal_is_not_durable_memory_until_owner_approves(tmp_path):
    store = MemoryStore(tmp_path / "workspace.sqlite3")
    proposal = store.create_proposal(
        title="Human agency",
        content="People retain authority over durable memory.",
        rationale="A deliberate owner-approved principle.",
    )

    assert proposal["status"] == "pending_review"
    assert store.list_memories() == []
    assert [event["event_type"] for event in store.list_events(proposal_id=proposal["id"])] == [
        "proposal_created"
    ]

    memory = store.approve(proposal["id"])
    assert memory["status"] == "active"
    assert memory["content"] == proposal["content"]
    assert store.get_proposal(proposal["id"])["status"] == "approved"
    assert [event["event_type"] for event in store.list_events(proposal_id=proposal["id"])] == [
        "proposal_created",
        "proposal_approved",
    ]


def test_memory_proposal_rejection_and_duplicate_approval_are_terminal(tmp_path):
    store = MemoryStore(tmp_path / "workspace.sqlite3")
    rejected = store.create_proposal(
        title="Rejected", content="Not retained.", rationale="Owner review."
    )
    assert store.reject(rejected["id"])["status"] == "rejected"
    with pytest.raises(ValueError, match="pending"):
        store.approve(rejected["id"])

    approved = store.create_proposal(
        title="Approved", content="Keep this.", rationale="Owner review."
    )
    store.approve(approved["id"])
    with pytest.raises(ValueError, match="pending"):
        store.approve(approved["id"])


def test_memory_source_references_must_match_a_real_document_chunk(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    documents = DocumentStore(database)
    document = documents.create("source.txt", "A source with traceable context.")
    store = MemoryStore(database)

    with pytest.raises(LookupError, match="not found"):
        store.create_proposal(
            title="Bad source",
            content="Unverified",
            rationale="Must reject invalid source links.",
            source_document_id=document["id"],
            source_chunk_id="missing",
        )

    proposal = store.create_proposal(
        title="Grounded memory",
        content="A source with traceable context.",
        rationale="Preserve source lineage.",
        source_document_id=document["id"],
        source_chunk_id=document["chunks"][0]["id"],
    )
    assert proposal["source_document_id"] == document["id"]
    assert proposal["source_chunk_id"] == document["chunks"][0]["id"]


def test_memory_archive_restore_and_event_history_are_append_only(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    store = MemoryStore(database)
    proposal = store.create_proposal(
        title="Lifecycle", content="Archive and restore.", rationale="Test lifecycle."
    )
    item = store.approve(proposal["id"])
    assert store.set_archived(item["id"], True)["status"] == "archived"
    assert store.list_memories(status="active") == []
    assert store.set_archived(item["id"], False)["status"] == "active"
    assert [event["event_type"] for event in store.list_events(memory_id=item["id"])] == [
        "proposal_approved",
        "memory_archived",
        "memory_restored",
    ]

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE memory_events SET actor = 'system' WHERE memory_id = ?",
                (item["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM memory_events WHERE memory_id = ?", (item["id"],)
            )


def test_memory_api_requires_auth_and_approval_is_a_separate_action(tmp_path):
    strict = TestClient(
        create_app(str(tmp_path / "strict.sqlite3")),
        client=("127.0.0.1", 50000),
    )
    assert strict.post(
        "/v1/memory/proposals",
        json={"title": "x", "content": "y", "rationale": "z"},
    ).status_code == 401

    client = TestClient(
        create_app(
            str(tmp_path / "local.sqlite3"), allow_unauthenticated_local=True
        ),
        client=("127.0.0.1", 50000),
    )
    created = client.post(
        "/v1/memory/proposals",
        json={
            "title": "Owner control",
            "content": "Approval is a distinct explicit action.",
            "rationale": "Never infer durable consent from model output.",
        },
    )
    assert created.status_code == 201
    proposal = created.json()
    assert proposal["status"] == "pending_review"
    assert client.get("/v1/memories").json()["items"] == []

    approved = client.post(f"/v1/memory/proposals/{proposal['id']}/approve")
    assert approved.status_code == 201
    assert approved.json()["status"] == "active"
    assert client.post(f"/v1/memory/proposals/{proposal['id']}/approve").status_code == 409
    assert client.post(f"/v1/memories/{approved.json()['id']}/archive").json()["status"] == "archived"
    assert client.post(f"/v1/memories/{approved.json()['id']}/restore").json()["status"] == "active"


def test_memory_lifecycle_round_trips_in_portable_workspace_export(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    app = create_app(str(source_db), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    source = client.post(
        "/v1/documents",
        json={"filename": "source.md", "content": "A source for approved memory."},
    ).json()
    proposal = client.post(
        "/v1/memory/proposals",
        json={
            "title": "Traceable",
            "content": "Memory stays connected to evidence.",
            "rationale": "Owner accepted this source-backed idea.",
            "source_document_id": source["id"],
            "source_chunk_id": source["chunks"][0]["id"],
        },
    ).json()
    memory = client.post(f"/v1/memory/proposals/{proposal['id']}/approve").json()
    client.post(f"/v1/memories/{memory['id']}/archive")

    exported = KnowledgeStore(source_db).export_workspace()
    assert exported["schema_version"] == "1.2.0"
    assert len(exported["tables"]["memory_proposals"]) == 1
    assert len(exported["tables"]["memory_items"]) == 1
    assert len(exported["tables"]["memory_events"]) == 3
    export_path = tmp_path / "workspace.json"
    export_path.write_text(json.dumps(exported, ensure_ascii=False), encoding="utf-8")

    target_db = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target_db), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    KnowledgeStore(target_db).import_workspace(export_path, tmp_path / "safety.sqlite3")
    imported = MemoryStore(target_db)
    assert imported.get_proposal(proposal["id"])["status"] == "approved"
    assert imported.get_memory(memory["id"])["status"] == "archived"
    assert [event["event_type"] for event in imported.list_events(memory_id=memory["id"])] == [
        "proposal_approved",
        "memory_archived",
    ]


def test_memory_export_rejects_invalid_lifecycle_even_with_recomputed_digest(tmp_path):
    database = tmp_path / "source.sqlite3"
    app = create_app(str(database), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    proposal = client.post(
        "/v1/memory/proposals",
        json={"title": "Pending", "content": "Not approved", "rationale": "Review."},
    ).json()
    exported = KnowledgeStore(database).export_workspace()
    exported["tables"]["memory_items"].append(
        {
            "id": "forged-memory",
            "proposal_id": proposal["id"],
            "title": "Forged",
            "content": "Not approved",
            "content_hash": "0" * 64,
            "rationale": "Forged state",
            "source_document_id": None,
            "source_chunk_id": None,
            "status": "active",
            "created_at": proposal["created_at"],
            "updated_at": proposal["created_at"],
        }
    )
    unsigned = {key: value for key, value in exported.items() if key != "integrity"}
    import hashlib

    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    exported["integrity"]["canonical_document_sha256"] = hashlib.sha256(canonical).hexdigest()
    export_path = tmp_path / "forged.json"
    export_path.write_text(json.dumps(exported, ensure_ascii=False), encoding="utf-8")

    target_db = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target_db), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    with pytest.raises(ValueError, match="explicitly approved"):
        KnowledgeStore(target_db).import_workspace(export_path, tmp_path / "safety.sqlite3")
    assert not (tmp_path / "safety.sqlite3").exists()
