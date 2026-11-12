import hashlib
import json

from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.cli import main
from humanity_os.store import KnowledgeStore


def test_full_workspace_export_covers_domain_history_and_excludes_secrets(tmp_path):
    database = tmp_path / "workspace.sqlite3"
    app = create_app(str(database), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    created = client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Export me", "content": "Portable content"},
    )
    assert created.status_code == 201
    record = created.json()
    updated = client.put(
        f"/v1/knowledge/{record['id']}",
        json={"kind": "observation", "title": "Export me v2", "content": "Updated content"},
    )
    assert updated.status_code == 200

    response = client.get("/v1/workspace/export")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    document = response.json()
    assert document["format"] == "humanity-os-workspace"
    assert document["schema_version"] == "1.0.0"
    assert len(document["tables"]["knowledge"]) == 1
    assert len(document["tables"]["knowledge_revisions"]) == 2
    assert "auth_audit_events" in document["tables"]
    assert "owner_identity" not in document["tables"]
    assert "auth_sessions" not in document["tables"]
    assert "auth_login_limits" not in document["tables"]
    assert all("password_hash" not in row for rows in document["tables"].values() for row in rows)

    integrity = document.pop("integrity")
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert integrity["algorithm"] == "sha256"
    assert integrity["canonical_document_sha256"] == hashlib.sha256(canonical).hexdigest()


def test_full_workspace_export_requires_authentication_by_default(tmp_path):
    app = create_app(str(tmp_path / "strict.sqlite3"))
    client = TestClient(app, client=("127.0.0.1", 50000))
    assert client.get("/v1/workspace/export").status_code == 401


def test_cli_workspace_deletion_requires_backup_and_removes_active_database(
    tmp_path, monkeypatch, capsys
):
    database = tmp_path / "active.sqlite3"
    backup = tmp_path / "pre-delete.sqlite3"
    app = create_app(str(database), allow_unauthenticated_local=True)
    client = TestClient(app, client=("127.0.0.1", 50000))
    assert client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "Delete target", "content": "Private"},
    ).status_code == 201

    monkeypatch.setenv("HUMANITY_OS_DB", str(database))
    monkeypatch.setattr(
        "sys.argv",
        ["humanity-os", "--delete-workspace", "--safety-backup", str(backup), "--confirm-delete"],
    )
    main()

    assert not database.exists()
    assert backup.exists()
    assert KnowledgeStore.verify_backup(backup) == 1
    output = capsys.readouterr().out
    assert "Verified safety backup retained" in output
    assert "not erased" in output

def test_portable_workspace_import_round_trips_domain_history_and_resets_identity(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    source_app = create_app(str(source_db), allow_unauthenticated_local=True)
    source_client = TestClient(source_app, client=("127.0.0.1", 50000))
    created = source_client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "Portable", "content": "Original"},
    ).json()
    source_client.put(
        f"/v1/knowledge/{created['id']}",
        json={"kind": "concept", "title": "Portable v2", "content": "Updated"},
    )
    export_path = tmp_path / "workspace.json"
    export_path.write_text(
        json.dumps(KnowledgeStore(source_db).export_workspace(), ensure_ascii=False),
        encoding="utf-8",
    )

    target_db = tmp_path / "target.sqlite3"
    target_app = create_app(str(target_db), allow_unauthenticated_local=True)
    target_client = TestClient(target_app, client=("127.0.0.1", 50000))
    target_client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Old target", "content": "Must be backed up"},
    )
    safety_backup = tmp_path / "pre-import.sqlite3"

    count = KnowledgeStore(target_db).import_workspace(export_path, safety_backup)

    imported = KnowledgeStore(target_db)
    assert count == 1
    assert imported.get(created["id"]).content == "Updated"
    assert [item.revision for item in imported.list_revisions(created["id"])] == [2, 1]
    assert imported.list()[0].title == "Portable v2"
    assert KnowledgeStore.verify_backup(safety_backup) == 1
    from humanity_os.auth import AuthStore

    assert not AuthStore(target_db).has_owner()


def test_portable_workspace_import_rejects_tampering_before_replacement(tmp_path):
    source_db = tmp_path / "source.sqlite3"
    source_app = create_app(str(source_db), allow_unauthenticated_local=True)
    source_client = TestClient(source_app, client=("127.0.0.1", 50000))
    source_client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "Original", "content": "Untampered"},
    )
    document = KnowledgeStore(source_db).export_workspace()
    document["tables"]["knowledge"][0]["payload"] = "{}"
    export_path = tmp_path / "tampered.json"
    export_path.write_text(json.dumps(document), encoding="utf-8")

    target_db = tmp_path / "target.sqlite3"
    target_app = create_app(str(target_db), allow_unauthenticated_local=True)
    target_client = TestClient(target_app, client=("127.0.0.1", 50000))
    target_client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Keep me", "content": "Target intact"},
    )

    with pytest.raises(ValueError, match="integrity"):
        KnowledgeStore(target_db).import_workspace(export_path, tmp_path / "safety.sqlite3")
    assert KnowledgeStore(target_db).list()[0].title == "Keep me"
    assert not (tmp_path / "safety.sqlite3").exists()
