import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.store import KnowledgeStore


def test_create_read_update_list_and_delete_knowledge(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    payload = {
        "kind": "observation",
        "title": "First note",
        "content": "A user-owned knowledge record.",
    }
    created = client.post("/v1/knowledge", json=payload)
    assert created.status_code == 201
    record = created.json()
    assert record["visibility"] == "private"
    assert client.get(f"/v1/knowledge/{record['id']}").json()["content"] == payload["content"]

    updated = client.put(
        f"/v1/knowledge/{record['id']}",
        json={**payload, "title": "Updated note", "visibility": "shared"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated note"
    assert updated.json()["visibility"] == "shared"

    assert len(client.get("/v1/knowledge").json()["items"]) == 1
    assert client.delete(f"/v1/knowledge/{record['id']}").status_code == 204
    assert client.get(f"/v1/knowledge/{record['id']}").status_code == 404


def test_rejects_unknown_fields(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    response = client.post(
        "/v1/knowledge",
        json={"kind": "claim", "title": "x", "content": "y", "admin": True},
    )
    assert response.status_code == 422


def test_health_endpoint(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    assert client.get("/health").json()["status"] == "ok"


def test_bearer_authentication_protects_knowledge_endpoints(tmp_path):
    token = "a" * 43
    client = TestClient(create_app(str(tmp_path / "authenticated.sqlite3"), api_token=token))
    payload = {"kind": "concept", "title": "private", "content": "protected"}

    assert client.get("/health").status_code == 200
    assert client.get("/v1/knowledge").status_code == 401
    assert client.get(
        "/v1/knowledge", headers={"Authorization": "Bearer wrong-token"}
    ).status_code == 401
    response = client.post(
        "/v1/knowledge", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert client.get(
        "/v1/knowledge", headers={"Authorization": f"Bearer {token}"}
    ).status_code == 200


def test_rejects_weak_api_token(tmp_path):
    with pytest.raises(ValueError, match="at least 32"):
        create_app(str(tmp_path / "weak.sqlite3"), api_token="too-short")


def test_invalid_cursor_is_rejected(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    assert client.get("/v1/knowledge?cursor=not-a-valid-cursor").status_code == 400


def test_search_and_json_export(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    client.post(
        "/v1/knowledge",
        json={"kind": "claim", "title": "Ocean research", "content": "Water samples"},
    )
    client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Garden", "content": "Tomatoes"},
    )
    results = client.get("/v1/knowledge?q=ocean").json()["items"]
    assert len(results) == 1
    assert results[0]["title"] == "Ocean research"
    exported = client.get("/v1/knowledge/export")
    assert exported.status_code == 200
    assert exported.json()["schema_version"] == "0.1"
    assert len(exported.json()["items"]) == 2


def test_pagination_and_literal_search_wildcards(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    for title in ("alpha", "beta", "gamma"):
        response = client.post(
            "/v1/knowledge",
            json={"kind": "concept", "title": title, "content": "100% reliable"},
        )
        assert response.status_code == 201

    first_page = client.get("/v1/knowledge?limit=2").json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"]
    second_page = client.get(
        "/v1/knowledge", params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 1
    assert not second_page["next_cursor"]

    literal_percent = client.get("/v1/knowledge?q=%25").json()["items"]
    assert len(literal_percent) == 3


def test_sqlite_backup_is_consistent_and_verifiable(tmp_path):
    database = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup dir" / "snapshot.sqlite3"
    client = TestClient(create_app(str(database)))
    for title in ("one", "two"):
        response = client.post(
            "/v1/knowledge",
            json={"kind": "concept", "title": title, "content": "backup test"},
        )
        assert response.status_code == 201

    created = KnowledgeStore(database).backup(backup)
    assert created == backup
    assert backup.stat().st_mode & 0o777 == 0o600
    assert KnowledgeStore.verify_backup(backup) == 2

    restored_view = KnowledgeStore(backup)
    assert len(restored_view.list()) == 2


def test_backup_never_overwrites_existing_destination(tmp_path):
    database = tmp_path / "source.sqlite3"
    destination = tmp_path / "existing.sqlite3"
    destination.write_text("keep this file", encoding="utf-8")
    store = KnowledgeStore(database)

    with pytest.raises(FileExistsError):
        store.backup(destination)

    assert destination.read_text(encoding="utf-8") == "keep this file"


def test_backup_rejects_active_database_as_destination(tmp_path):
    database = tmp_path / "source.sqlite3"
    store = KnowledgeStore(database)

    with pytest.raises(ValueError, match="differ"):
        store.backup(database)


def test_restore_validates_backup_and_preserves_pre_restore_snapshot(tmp_path):
    database = tmp_path / "active.sqlite3"
    backup = tmp_path / "known-good.sqlite3"
    safety = tmp_path / "pre-restore.sqlite3"
    store = KnowledgeStore(database)

    client = TestClient(create_app(str(database)))
    for title in ("original-a", "original-b"):
        response = client.post(
            "/v1/knowledge",
            json={"kind": "concept", "title": title, "content": "from backup"},
        )
        assert response.status_code == 201
    store.backup(backup)

    response = client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "newer-local", "content": "preserve me"},
    )
    assert response.status_code == 201
    assert len(store.list()) == 3

    assert store.restore(backup, safety) == 2
    assert len(store.list()) == 2
    assert {record.title for record in store.list()} == {"original-a", "original-b"}
    assert KnowledgeStore.verify_backup(safety) == 3


def test_restore_rejects_invalid_backup_without_touching_active_database(tmp_path):
    database = tmp_path / "active.sqlite3"
    invalid_backup = tmp_path / "invalid.sqlite3"
    safety = tmp_path / "pre-restore.sqlite3"
    store = KnowledgeStore(database)
    client = TestClient(create_app(str(database)))
    client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "keep", "content": "active data"},
    )
    invalid_backup.write_text("not a sqlite database", encoding="utf-8")

    with pytest.raises(sqlite3.DatabaseError):
        store.restore(invalid_backup, safety)

    assert [record.title for record in store.list()] == ["keep"]
    assert not safety.exists()


def test_cli_restore_requires_explicit_confirmation(tmp_path, monkeypatch):
    from humanity_os.cli import main

    database = tmp_path / "active.sqlite3"
    store = KnowledgeStore(database)
    backup = tmp_path / "backup.sqlite3"
    store.backup(backup)
    safety = tmp_path / "safety.sqlite3"
    monkeypatch.setenv("HUMANITY_OS_DB", str(database))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "humanity-os",
            "--restore-from",
            str(backup),
            "--safety-backup",
            str(safety),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert not safety.exists()
