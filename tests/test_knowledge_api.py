import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.store import KnowledgeStore


def test_create_read_update_list_and_delete_knowledge(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    payload = {"kind": "observation", "title": "First note", "content": "A user-owned knowledge record."}
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
    assert client.get("/v1/knowledge", headers={"Authorization": "Bearer wrong-token"}).status_code == 401
    response = client.post(
        "/v1/knowledge", json=payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert client.get("/v1/knowledge", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_rejects_weak_api_token(tmp_path):
    with pytest.raises(ValueError, match="at least 32"):
        create_app(str(tmp_path / "weak.sqlite3"), api_token="too-short")


def test_cli_generates_a_256_bit_token_without_opening_the_database(tmp_path, monkeypatch, capsys):
    from humanity_os.cli import main
    monkeypatch.setenv("HUMANITY_OS_DB", str(tmp_path / "must-not-exist.sqlite3"))
    monkeypatch.setattr(sys, "argv", ["humanity-os", "--generate-api-token"])
    main()
    assert len(capsys.readouterr().out.strip()) == 43
    assert not (tmp_path / "must-not-exist.sqlite3").exists()


def test_owner_session_requires_csrf_and_can_be_revoked(tmp_path):
    database = str(tmp_path / "owner.sqlite3")
    app = create_app(database)
    app.state.auth_store.set_owner_password("a long secure test password")
    client = TestClient(app)

    assert client.get("/v1/knowledge").status_code == 401
    login = client.post("/auth/login", json={"password": "a long secure test password"})
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]
    assert client.cookies.get("humanity_session")
    assert client.get("/v1/knowledge").status_code == 200

    blocked = client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "blocked", "content": "missing csrf"},
    )
    assert blocked.status_code == 403

    created = client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "allowed", "content": "valid csrf"},
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201

    logged_out = client.post("/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logged_out.status_code == 204
    assert client.get("/v1/knowledge").status_code == 401


def test_owner_login_rejects_wrong_password_and_short_password_is_rejected(tmp_path):
    app = create_app(str(tmp_path / "owner.sqlite3"))
    with pytest.raises(ValueError, match="12 characters"):
        app.state.auth_store.set_owner_password("short")
    app.state.auth_store.set_owner_password("a long secure test password")
    client = TestClient(app)
    assert client.post("/auth/login", json={"password": "incorrect password"}).status_code == 401


def test_password_rotation_revokes_existing_sessions(tmp_path):
    app = create_app(str(tmp_path / "owner.sqlite3"))
    app.state.auth_store.set_owner_password("first secure password")
    client = TestClient(app)
    login = client.post("/auth/login", json={"password": "first secure password"})
    assert login.status_code == 200
    app.state.auth_store.set_owner_password("second secure password")
    assert client.get("/v1/knowledge").status_code == 401
    assert client.post("/auth/login", json={"password": "second secure password"}).status_code == 200


def test_invalid_cursor_is_rejected(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    assert client.get("/v1/knowledge?cursor=not-a-valid-cursor").status_code == 400


def test_search_and_json_export(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    client.post("/v1/knowledge", json={"kind": "claim", "title": "Ocean research", "content": "Water samples"})
    client.post("/v1/knowledge", json={"kind": "observation", "title": "Garden", "content": "Tomatoes"})
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
    assert len(client.get("/v1/knowledge?q=%25").json()["items"]) == 3


def test_sqlite_backup_is_consistent_and_verifiable(tmp_path):
    database = tmp_path / "source.sqlite3"
    backup = tmp_path / "backup dir" / "snapshot.sqlite3"
    client = TestClient(create_app(str(database)))
    for title in ("one", "two"):
        assert client.post(
            "/v1/knowledge",
            json={"kind": "concept", "title": title, "content": "backup test"},
        ).status_code == 201
    created = KnowledgeStore(database).backup(backup)
    assert created == backup
    assert backup.stat().st_mode & 0o777 == 0o600
    assert KnowledgeStore.verify_backup(backup) == 2
    assert len(KnowledgeStore(backup).list()) == 2


def test_backup_never_overwrites_existing_destination(tmp_path):
    database = tmp_path / "source.sqlite3"
    destination = tmp_path / "existing.sqlite3"
    destination.write_text("keep this file", encoding="utf-8")
    with pytest.raises(FileExistsError):
        KnowledgeStore(database).backup(destination)
    assert destination.read_text(encoding="utf-8") == "keep this file"


def test_backup_rejects_active_database_as_destination(tmp_path):
    database = tmp_path / "source.sqlite3"
    with pytest.raises(ValueError, match="differ"):
        KnowledgeStore(database).backup(database)


def test_restore_validates_backup_and_preserves_pre_restore_snapshot(tmp_path):
    database, backup, safety = (tmp_path / name for name in ("active.sqlite3", "known-good.sqlite3", "pre-restore.sqlite3"))
    store = KnowledgeStore(database)
    client = TestClient(create_app(str(database)))
    for title in ("original-a", "original-b"):
        assert client.post(
            "/v1/knowledge",
            json={"kind": "concept", "title": title, "content": "from backup"},
        ).status_code == 201
    store.backup(backup)
    assert client.post(
        "/v1/knowledge",
        json={"kind": "concept", "title": "newer-local", "content": "preserve me"},
    ).status_code == 201
    assert len(store.list()) == 3
    assert store.restore(backup, safety) == 2
    assert {record.title for record in store.list()} == {"original-a", "original-b"}
    assert KnowledgeStore.verify_backup(safety) == 3


def test_restore_rejects_invalid_backup_without_touching_active_database(tmp_path):
    database, invalid_backup, safety = (tmp_path / name for name in ("active.sqlite3", "invalid.sqlite3", "pre-restore.sqlite3"))
    store = KnowledgeStore(database)
    client = TestClient(create_app(str(database)))
    client.post("/v1/knowledge", json={"kind": "concept", "title": "keep", "content": "active data"})
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
    monkeypatch.setattr(sys, "argv", ["humanity-os", "--restore-from", str(backup), "--safety-backup", str(safety)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert not safety.exists()


def test_owner_login_is_rate_limited_after_five_failures(tmp_path):
    app = create_app(str(tmp_path / "owner.sqlite3"))
    app.state.auth_store.set_owner_password("a long secure test password")
    client = TestClient(app)

    for _ in range(5):
        response = client.post("/auth/login", json={"password": "incorrect password"})
        assert response.status_code == 401

    blocked = client.post("/auth/login", json={"password": "a long secure test password"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0



def test_auth_audit_events_are_recorded_and_append_only(tmp_path):
    database = tmp_path / "owner.sqlite3"
    app = create_app(str(database))
    app.state.auth_store.set_owner_password("a long secure test password")
    client = TestClient(app)

    failed = client.post("/auth/login", json={"password": "incorrect password"})
    assert failed.status_code == 401
    login = client.post("/auth/login", json={"password": "a long secure test password"})
    assert login.status_code == 200
    csrf = login.json()["csrf_token"]

    events = client.get("/auth/events").json()["items"]
    event_types = [event["event_type"] for event in events]
    assert "owner_password_changed" in event_types
    assert "login_failed" in event_types
    assert "login_succeeded" in event_types
    assert "session_created" in event_types
    assert all("a long secure test password" not in str(event) for event in events)

    event_id = events[0]["id"]
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE auth_audit_events SET event_type = 'tampered' WHERE id = ?",
                (event_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM auth_audit_events WHERE id = ?", (event_id,))

    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert any(
        event["event_type"] == "session_revoked"
        for event in app.state.auth_store.list_audit_events()
    )


def test_auth_audit_event_pagination_is_bounded(tmp_path):
    app = create_app(str(tmp_path / "owner.sqlite3"))
    auth = app.state.auth_store
    for index in range(5):
        auth.record_audit_event("test_event", f"item-{index}")
    first = auth.list_audit_events(limit=2)
    assert len(first) == 2
    second = auth.list_audit_events(limit=2, before_id=first[-1]["id"])
    assert len(second) == 2
    assert first[0]["id"] > second[0]["id"]
    with pytest.raises(ValueError, match="between 1 and 100"):
        auth.list_audit_events(limit=101)


def test_knowledge_provenance_sources_and_evidence_round_trip(tmp_path):
    client = TestClient(create_app(str(tmp_path / "provenance.sqlite3")))
    source = {
        "id": "source-paper-1",
        "uri": "https://example.org/research/paper",
        "title": "Research paper",
        "publisher": "Example Institute",
        "content_hash": "a" * 64,
    }
    payload = {
        "kind": "claim",
        "title": "A sourced claim",
        "content": "A statement with traceable evidence.",
        "sources": [source],
        "evidence": [{
            "id": "evidence-1",
            "source_id": "source-paper-1",
            "relation": "supports",
            "excerpt": "A short supporting excerpt.",
            "locator": "page 4",
        }],
    }
    created = client.post("/v1/knowledge", json=payload)
    assert created.status_code == 201
    record_id = created.json()["id"]

    fetched = client.get(f"/v1/knowledge/{record_id}")
    assert fetched.status_code == 200
    assert fetched.json()["sources"][0]["content_hash"] == "a" * 64
    assert fetched.json()["evidence"][0]["source_id"] == "source-paper-1"
    exported = client.get("/v1/knowledge/export").json()
    assert exported["items"][0]["evidence"][0]["relation"] == "supports"


def test_knowledge_evidence_must_reference_declared_source(tmp_path):
    client = TestClient(create_app(str(tmp_path / "provenance.sqlite3")))
    response = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Untraceable claim",
        "content": "Evidence must point to a declared source.",
        "evidence": [{
            "source_id": "missing-source",
            "relation": "supports",
        }],
    })
    assert response.status_code == 422


def test_knowledge_provenance_rejects_invalid_hash_and_duplicate_source_ids(tmp_path):
    client = TestClient(create_app(str(tmp_path / "provenance.sqlite3")))
    invalid_hash = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Bad hash",
        "content": "Invalid source hash must be rejected.",
        "sources": [{"id": "s1", "uri": "https://example.org", "content_hash": "not-a-hash"}],
    })
    assert invalid_hash.status_code == 422

    duplicate_ids = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Duplicate source",
        "content": "Source identifiers must be unique.",
        "sources": [
            {"id": "same", "uri": "https://example.org/one"},
            {"id": "same", "uri": "https://example.org/two"},
        ],
    })
    assert duplicate_ids.status_code == 422


def test_conflict_registry_requires_two_records_and_human_decision(tmp_path):
    client = TestClient(create_app(str(tmp_path / "conflicts.sqlite3")))
    records = []
    for title in ("Claim A", "Claim B"):
        response = client.post(
            "/v1/knowledge",
            json={"kind": "claim", "title": title, "content": f"Content for {title}"},
        )
        assert response.status_code == 201
        records.append(response.json()["id"])

    self_conflict = client.post("/v1/conflicts", json={
        "record_a_id": records[0],
        "record_b_id": records[0],
        "reason": "A record cannot conflict with itself.",
    })
    assert self_conflict.status_code == 422

    missing = client.post("/v1/conflicts", json={
        "record_a_id": records[0],
        "record_b_id": "missing-record",
        "reason": "The second record is absent.",
    })
    assert missing.status_code == 404

    created = client.post("/v1/conflicts", json={
        "record_a_id": records[0],
        "record_b_id": records[1],
        "reason": "The claims appear inconsistent.",
    })
    assert created.status_code == 201
    conflict = created.json()
    assert conflict["status"] == "pending_review"
    assert conflict["resolution_note"] is None

    duplicate = client.post("/v1/conflicts", json={
        "record_a_id": records[1],
        "record_b_id": records[0],
        "reason": "Same pair, reversed order.",
    })
    assert duplicate.status_code == 409

    pending = client.get("/v1/conflicts?status=pending_review").json()["items"]
    assert len(pending) == 1
    decision = client.post(
        f"/v1/conflicts/{conflict['id']}/decision",
        json={"status": "resolved", "resolution_note": "Owner reviewed both sources."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "resolved"

    repeated = client.post(
        f"/v1/conflicts/{conflict['id']}/decision",
        json={"status": "dismissed", "resolution_note": "Second decision is not allowed."},
    )
    assert repeated.status_code == 409
    assert client.get("/v1/conflicts?status=resolved").json()["items"][0]["id"] == conflict["id"]


def test_conflict_decision_requires_a_resolution_note(tmp_path):
    client = TestClient(create_app(str(tmp_path / "conflicts.sqlite3")))
    first = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "One", "content": "One"
    }).json()["id"]
    second = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Two", "content": "Two"
    }).json()["id"]
    conflict = client.post("/v1/conflicts", json={
        "record_a_id": first, "record_b_id": second, "reason": "Potential contradiction."
    }).json()
    response = client.post(
        f"/v1/conflicts/{conflict['id']}/decision",
        json={"status": "resolved", "resolution_note": ""},
    )
    assert response.status_code == 422


def test_conflicts_survive_backup_and_restore_verification(tmp_path):
    database = tmp_path / "active.sqlite3"
    backup = tmp_path / "snapshot.sqlite3"
    client = TestClient(create_app(str(database)))
    first = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "First", "content": "First claim"
    }).json()["id"]
    second = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Second", "content": "Second claim"
    }).json()["id"]
    created = client.post("/v1/conflicts", json={
        "record_a_id": first, "record_b_id": second, "reason": "Need review."
    })
    assert created.status_code == 201
    KnowledgeStore(database).backup(backup)
    assert KnowledgeStore.verify_backup(backup) == 2
    assert len(KnowledgeStore(backup).list_conflicts()) == 1


def test_knowledge_record_with_conflict_cannot_be_deleted_silently(tmp_path):
    client = TestClient(create_app(str(tmp_path / "conflicts.sqlite3")))
    first = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Protected A", "content": "Claim A"
    }).json()["id"]
    second = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Protected B", "content": "Claim B"
    }).json()["id"]
    conflict = client.post("/v1/conflicts", json={
        "record_a_id": first, "record_b_id": second, "reason": "Review before deletion."
    })
    assert conflict.status_code == 201
    assert client.delete(f"/v1/knowledge/{first}").status_code == 409
    assert client.get(f"/v1/knowledge/{first}").status_code == 200
    assert client.get("/v1/conflicts").json()["items"][0]["id"] == conflict.json()["id"]


def test_restore_migrates_legacy_snapshot_without_conflict_table(tmp_path):
    legacy_database = tmp_path / "legacy-source.sqlite3"
    legacy_backup = tmp_path / "legacy-backup.sqlite3"
    active_database = tmp_path / "active.sqlite3"
    safety_backup = tmp_path / "safety.sqlite3"

    legacy_client = TestClient(create_app(str(legacy_database)))
    assert legacy_client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Legacy", "content": "Older schema record"
    }).status_code == 201
    KnowledgeStore(legacy_database).backup(legacy_backup)
    with sqlite3.connect(legacy_backup) as connection:
        connection.execute("DROP TABLE knowledge_conflicts")

    active_client = TestClient(create_app(str(active_database)))
    assert active_client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Current", "content": "Current schema record"
    }).status_code == 201

    restored = KnowledgeStore(active_database).restore(legacy_backup, safety_backup)
    assert restored == 1
    restored_store = KnowledgeStore(active_database)
    assert [record.title for record in restored_store.list()] == ["Legacy"]
    assert restored_store.list_conflicts() == []



def test_knowledge_updates_create_immutable_revision_history(tmp_path):
    client = TestClient(create_app(str(tmp_path / "revisions.sqlite3")))
    created = client.post("/v1/knowledge", json={
        "kind": "claim", "title": "Original", "content": "First state"
    })
    assert created.status_code == 201
    record = created.json()
    record_id = record["id"]
    assert record["revision"] == 1

    updated = client.put(f"/v1/knowledge/{record_id}", json={
        "kind": "claim", "title": "Revised", "content": "Second state"
    })
    assert updated.status_code == 200
    assert updated.json()["revision"] == 2

    history = client.get(f"/v1/knowledge/{record_id}/revisions")
    assert history.status_code == 200
    revisions = history.json()
    assert [item["revision"] for item in revisions] == [2, 1]
    assert revisions[0]["snapshot"]["title"] == "Revised"
    assert revisions[1]["snapshot"]["title"] == "Original"
    assert revisions[1]["snapshot"]["content"] == "First state"
    assert revisions[0]["change_reason"] == "updated via API"


def test_revision_history_rejects_unknown_record_and_bounds_limit(tmp_path):
    client = TestClient(create_app(str(tmp_path / "revisions.sqlite3")))
    assert client.get("/v1/knowledge/missing/revisions").status_code == 404
    record = client.post("/v1/knowledge", json={
        "kind": "concept", "title": "History", "content": "One"
    }).json()
    assert client.get(f"/v1/knowledge/{record['id']}/revisions?limit=101").status_code == 422


def test_revision_history_survives_backup_and_restore(tmp_path):
    database = tmp_path / "active.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    safety = tmp_path / "safety.sqlite3"
    client = TestClient(create_app(str(database)))
    created = client.post("/v1/knowledge", json={
        "kind": "observation", "title": "Before", "content": "v1"
    }).json()
    client.put(f"/v1/knowledge/{created['id']}", json={
        "kind": "observation", "title": "After", "content": "v2"
    })
    store = KnowledgeStore(database)
    store.backup(backup)
    assert store.verify_backup(backup) == 1
    store.restore(backup, safety)
    restored = KnowledgeStore(database)
    history = restored.list_revisions(created["id"])
    assert [item.revision for item in history] == [2, 1]


def test_revision_history_is_not_mutated_by_later_updates(tmp_path):
    database = tmp_path / "revisions.sqlite3"
    client = TestClient(create_app(str(database)))
    record = client.post("/v1/knowledge", json={
        "kind": "concept", "title": "v1", "content": "original"
    }).json()
    for version in (2, 3):
        response = client.put(f"/v1/knowledge/{record['id']}", json={
            "kind": "concept", "title": f"v{version}", "content": f"content-{version}"
        })
        assert response.json()["revision"] == version
    history = KnowledgeStore(database).list_revisions(record["id"])
    assert [item.snapshot.title for item in history] == ["v3", "v2", "v1"]
    assert [item.revision for item in history] == [3, 2, 1]
