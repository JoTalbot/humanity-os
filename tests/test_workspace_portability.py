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
        json={"kind": "note", "title": "Delete target", "content": "Private"},
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
