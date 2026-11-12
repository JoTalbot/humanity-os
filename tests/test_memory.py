from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.documents import DocumentStore
from humanity_os.memory import MemoryStore
from humanity_os.store import KnowledgeStore


def test_proposal_is_not_memory_until_explicit_approval(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    store = MemoryStore(database)
    proposal = store.create_proposal(
        title="Preferred language",
        content="The workspace should preserve the owner's chosen language.",
        rationale="Explicitly captured preference.",
    )

    assert proposal["status"] == "pending_review"
    assert store.list_memories() == []
    assert store.get_memory(proposal["id"]) is None

    memory = store.approve(proposal["id"])
    assert memory["status"] == "active"
    assert memory["proposal_id"] == proposal["id"]
    assert store.get_proposal(proposal["id"])["approved_memory_id"] == memory["id"]
    assert [event["event_type"] for event in store.list_events(proposal_id=proposal["id"])] == [
        "proposal_created",
        "proposal_approved",
    ]
    with pytest.raises(ValueError, match="Only pending"):
        store.approve(proposal["id"])


def test_proposal_rejection_never_creates_memory(tmp_path):
    store = MemoryStore(tmp_path / "workspace.sqlite3")
    proposal = store.create_proposal(
        title="Maybe",
        content="A proposed memory.",
        rationale="Needs owner review.",
    )
    rejected = store.reject(proposal["id"])
    assert rejected["status"] == "rejected"
    assert store.list_memories() == []
    with pytest.raises(ValueError, match="Only pending"):
        store.approve(proposal["id"])


def test_memory_source_must_resolve_to_exact_document_chunk(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    documents = DocumentStore(database)
    document = documents.create("source.md", "A source paragraph.")
    chunk = document["chunks"][0]
    memory = MemoryStore(database)

    proposal = memory.create_proposal(
        title="Sourced note",
        content="A retained note grounded in a document.",
        rationale="Owner-selected source context.",
        source_document_id=document["id"],
        source_chunk_id=chunk["id"],
    )
    approved = memory.approve(proposal["id"])
    assert approved["source_document_id"] == document["id"]
    assert approved["source_chunk_id"] == chunk["id"]

    with pytest.raises(LookupError, match="not found"):
        memory.create_proposal(
            title="Bad source",
            content="Unlinked.",
            rationale="Invalid provenance.",
            source_document_id=document["id"],
            source_chunk_id="missing-chunk",
        )
    with pytest.raises(ValueError, match="supplied together"):
        memory.create_proposal(
            title="Incomplete source",
            content="Unlinked.",
            rationale="Incomplete provenance.",
            source_document_id=document["id"],
        )


def test_memory_archive_restore_is_explicit_and_audited(tmp_path):
    store = MemoryStore(tmp_path / "workspace.sqlite3")
    proposal = store.create_proposal(
        title="Archive lifecycle",
        content="This memory can be archived and restored.",
        rationale="Lifecycle test.",
    )
    item = store.approve(proposal["id"])
    archived = store.set_archived(item["id"], True)
    assert archived["status"] == "archived"
    restored = store.set_archived(item["id"], False)
    assert restored["status"] == "active"
    events = store.list_events(memory_id=item["id"])
    assert [event["event_type"] for event in events] == [
        "proposal_approved",
        "memory_archived",
        "memory_restored",
    ]
    with pytest.raises(ValueError, match="already active"):
        store.set_archived(item["id"], False)


def test_memory_api_requires_authentication_and_separate_approval(tmp_path):
    strict = TestClient(
        create_app(str(tmp_path / "strict.sqlite3")),
        client=("127.0.0.1", 50000),
    )
    assert strict.post(
        "/v1/memory/proposals",
        json={"title": "x", "content": "y", "rationale": "z"},
    ).status_code == 401

    client = TestClient(
        create_app(str(tmp_path / "local.sqlite3"), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    response = client.post(
        "/v1/memory/proposals",
        json={
            "title": "Human review",
            "content": "Only owner approval makes this durable.",
            "rationale": "A test proposal.",
        },
    )
    assert response.status_code == 201
    proposal = response.json()
    assert proposal["status"] == "pending_review"
    assert client.get("/v1/memories").json()["items"] == []
    approved = client.post(f"/v1/memory/proposals/{proposal['id']}/approve")
    assert approved.status_code == 201
    assert approved.json()["status"] == "active"
    assert client.get("/v1/memories").json()["items"][0]["id"] == approved.json()["id"]
    assert client.post(f"/v1/memory/proposals/{proposal['id']}/approve").status_code == 409


def test_memory_api_validates_document_source_and_archives(tmp_path):
    client = TestClient(
        create_app(str(tmp_path / "workspace.sqlite3"), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    document = client.post(
        "/v1/documents",
        json={"filename": "source.txt", "content": "Source for a saved memory."},
    ).json()
    chunk = document["chunks"][0]
    response = client.post(
        "/v1/memory/proposals",
        json={
            "title": "Sourced",
            "content": "Remember this source fact.",
            "rationale": "Owner approved source context.",
            "source_document_id": document["id"],
            "source_chunk_id": chunk["id"],
        },
    )
    assert response.status_code == 201
    approved = client.post(f"/v1/memory/proposals/{response.json()['id']}/approve")
    memory_id = approved.json()["id"]
    assert client.post(f"/v1/memories/{memory_id}/archive").json()["status"] == "archived"
    assert client.post(f"/v1/memories/{memory_id}/restore").json()["status"] == "active"
    assert client.get("/v1/memory/events", params={"proposal_id": response.json()["id"]}).status_code == 200


def test_memory_export_import_round_trip_and_secret_exclusion(tmp_path):
    source = tmp_path / "source.sqlite3"
    client = TestClient(
        create_app(str(source), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    proposal = client.post(
        "/v1/memory/proposals",
        json={"title": "Portable memory", "content": "Export this selected memory.", "rationale": "Owner choice."},
    ).json()
    client.post(f"/v1/memory/proposals/{proposal['id']}/approve")
    exported = KnowledgeStore(source).export_workspace()
    assert exported["schema_version"] == "1.2.0"
    assert len(exported["tables"]["memory_proposals"]) == 1
    assert len(exported["tables"]["memory_items"]) == 1
    assert len(exported["tables"]["memory_events"]) == 2
    assert all("password_hash" not in row for rows in exported["tables"].values() for row in rows)

    export_path = tmp_path / "workspace.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")
    target = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")
    restored = MemoryStore(target).list_memories()
    assert len(restored) == 1
    assert restored[0]["content"] == "Export this selected memory."


def test_memory_import_rejects_domain_tampering_even_with_recomputed_digest(tmp_path):
    source = tmp_path / "source.sqlite3"
    client = TestClient(
        create_app(str(source), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    proposal = client.post(
        "/v1/memory/proposals",
        json={"title": "Tamper", "content": "Original memory content.", "rationale": "Test."},
    ).json()
    client.post(f"/v1/memory/proposals/{proposal['id']}/approve")
    exported = KnowledgeStore(source).export_workspace()
    exported["tables"]["memory_items"][0]["content_hash"] = hashlib.sha256(
        b"forged content"
    ).hexdigest()
    unsigned = {key: value for key, value in exported.items() if key != "integrity"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    exported["integrity"]["canonical_document_sha256"] = hashlib.sha256(canonical).hexdigest()
    export_path = tmp_path / "forged.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")

    target = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    with pytest.raises(ValueError, match="explicitly approved proposal"):
        KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")
    assert not (tmp_path / "safety.sqlite3").exists()


def test_memory_events_are_append_only(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    store = MemoryStore(database)
    proposal = store.create_proposal(
        title="Immutable event",
        content="The event must not be rewritten.",
        rationale="Audit test.",
    )
    event = store.list_events(proposal_id=proposal["id"])[0]
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE memory_events SET event_type = 'rewritten' WHERE id = ?",
                (event["id"],),
            )
