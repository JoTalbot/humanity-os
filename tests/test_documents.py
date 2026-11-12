from __future__ import annotations

import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.documents import CHUNK_SIZE, DocumentStore
from humanity_os.store import KnowledgeStore


def test_text_document_is_chunked_with_exact_source_offsets(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    store = DocumentStore(database)
    content = ("A paragraph about local knowledge.\n" * 100).strip()
    document = store.create("notes.md", content)

    assert document["status"] == "ready"
    assert document["media_type"] == "text/markdown"
    assert document["content_hash"] == hashlib.sha256(content.encode()).hexdigest()
    assert document["chunk_count"] == len(document["chunks"])
    assert document["chunks"][0]["start_offset"] == 0
    for chunk in document["chunks"]:
        assert content[chunk["start_offset"]:chunk["end_offset"]] == chunk["content"]
        assert chunk["content_hash"] == hashlib.sha256(chunk["content"].encode()).hexdigest()
    if len(document["chunks"]) > 1:
        assert document["chunks"][1]["start_offset"] <= CHUNK_SIZE
        assert document["chunks"][1]["start_offset"] < document["chunks"][0]["end_offset"]


def test_document_input_is_allowlisted_bounded_and_deduplicated(tmp_path):
    store = DocumentStore(tmp_path / "workspace.sqlite3")
    with pytest.raises(ValueError, match="Only"):
        store.create("payload.pdf", "not a supported parser")
    with pytest.raises(ValueError, match="NUL"):
        store.create("bad.txt", "hello\x00world")
    with pytest.raises(ValueError, match="non-empty"):
        store.create("empty.txt", "  ")
    store.create("one.txt", "same content")
    with pytest.raises(ValueError, match="identical content"):
        store.create("two.md", "same content")
    with pytest.raises(ValueError, match="identical content"):
        store.create("two.md", "same content")


def test_source_aware_search_returns_document_and_chunk_references(tmp_path):
    store = DocumentStore(tmp_path / "workspace.sqlite3")
    document = store.create("research.txt", "Quantum systems preserve source provenance.")
    results = store.search("quantum provenance")

    assert len(results) == 1
    assert results[0]["document_id"] == document["id"]
    assert results[0]["chunk_id"] == document["chunks"][0]["id"]
    assert results[0]["excerpt"] == "Quantum systems preserve source provenance."
    assert results[0]["start_offset"] == 0


def test_document_api_is_authenticated_by_default_and_supports_search(tmp_path):
    strict = TestClient(create_app(str(tmp_path / "strict.sqlite3")), client=("127.0.0.1", 50000))
    assert strict.post(
        "/v1/documents", json={"filename": "notes.txt", "content": "Private text"}
    ).status_code == 401

    app = create_app(str(tmp_path / "local.sqlite3"), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    created = client.post(
        "/v1/documents",
        json={"filename": "notes.txt", "content": "Humanity needs traceable knowledge."},
    )
    assert created.status_code == 201
    document = created.json()
    assert client.get(f"/v1/documents/{document['id']}").json()["id"] == document["id"]
    found = client.post("/v1/documents/search", json={"query": "traceable knowledge"})
    assert found.status_code == 200
    assert found.json()["items"][0]["document_id"] == document["id"]
    assert found.json()["items"][0]["chunk_id"] == document["chunks"][0]["id"]
    assert client.post(
        "/v1/documents", json={"filename": "scan.pdf", "content": "binary omitted"}
    ).status_code == 422


def test_workspace_export_and_import_round_trip_document_content(tmp_path):
    source = tmp_path / "source.sqlite3"
    source_app = create_app(str(source), allow_unauthenticated_local=True)
    client = TestClient(source_app, client=("127.0.0.1", 50000))
    created = client.post(
        "/v1/documents",
        json={"filename": "handover.md", "content": "A locally stored source document."},
    ).json()

    exported = KnowledgeStore(source).export_workspace()
    assert exported["schema_version"] == "1.1.0"
    assert len(exported["tables"]["documents"]) == 1
    assert len(exported["tables"]["document_chunks"]) == 1
    export_path = tmp_path / "workspace.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")

    target = tmp_path / "target.sqlite3"
    target_app = create_app(str(target), allow_unauthenticated_local=True)
    TestClient(target_app, client=("127.0.0.1", 50000))
    KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")
    imported = DocumentStore(target).get(created["id"])
    assert imported["content_hash"] == created["content_hash"]
    assert imported["chunks"][0]["content"] == "A locally stored source document."


def test_document_export_tampering_is_rejected_before_import(tmp_path):
    source = tmp_path / "source.sqlite3"
    client = TestClient(
        create_app(str(source), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    client.post(
        "/v1/documents", json={"filename": "notes.txt", "content": "original content"}
    )
    exported = KnowledgeStore(source).export_workspace()
    exported["tables"]["documents"][0]["content"] = "tampered"
    export_path = tmp_path / "tampered.json"
    export_path.write_text(json.dumps(exported), encoding="utf-8")

    target = tmp_path / "target.sqlite3"
    TestClient(
        create_app(str(target), allow_unauthenticated_local=True),
        client=("127.0.0.1", 50000),
    )
    with pytest.raises(ValueError, match="integrity"):
        KnowledgeStore(target).import_workspace(export_path, tmp_path / "safety.sqlite3")
    assert not (tmp_path / "safety.sqlite3").exists()
