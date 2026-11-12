import sqlite3

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.models import KnowledgeSource
from humanity_os.store import KnowledgeStore


def _knowledge_payload():
    return {
        "kind": "claim",
        "title": "A testable claim",
        "content": "A claim with declared evidence.",
        "sources": [
            {
                "id": "primary",
                "uri": "HTTPS://Example.ORG:443/report#section",
                "source_type": "primary",
                "independence_group_id": "origin-a",
            },
            {
                "id": "syndicated",
                "uri": "https://mirror.example.org/report",
                "source_type": "secondary",
                "independence_group_id": "origin-a",
                "derived_from_source_ids": ["primary"],
            },
        ],
        "evidence": [
            {
                "id": "evidence-1",
                "source_id": "primary",
                "relation": "supports",
                "excerpt": "A bounded excerpt.",
            }
        ],
    }


def test_source_canonical_uri_normalizes_scheme_host_port_and_fragment():
    source = KnowledgeSource(uri="HTTPS://Example.ORG:443/report#section")
    assert source.canonical_uri == "https://example.org/report"


def test_duplicate_canonical_source_uri_is_rejected(tmp_path):
    client = TestClient(create_app(str(tmp_path / "duplicate-uri.sqlite3")))
    payload = _knowledge_payload()
    payload["sources"][1]["uri"] = "https://example.org/report"
    payload["sources"][1]["derived_from_source_ids"] = []
    payload["sources"][1]["independence_group_id"] = "origin-b"
    assert client.post("/v1/knowledge", json=payload).status_code == 422


def test_source_lineage_rejects_missing_references_and_cycles(tmp_path):
    client = TestClient(create_app(str(tmp_path / "lineage.sqlite3")))
    payload = _knowledge_payload()
    payload["sources"][1]["derived_from_source_ids"] = ["missing"]
    assert client.post("/v1/knowledge", json=payload).status_code == 422

    payload = _knowledge_payload()
    payload["sources"][0]["derived_from_source_ids"] = ["syndicated"]
    assert client.post("/v1/knowledge", json=payload).status_code == 422


def test_evidence_assessment_requires_declared_source_and_matching_evidence(tmp_path):
    client = TestClient(create_app(str(tmp_path / "assessment-validation.sqlite3")))
    record = client.post("/v1/knowledge", json=_knowledge_payload()).json()
    missing_source = client.post("/v1/evidence-assessments", json={
        "knowledge_id": record["id"],
        "source_id": "unknown",
        "stance": "supports",
        "status": "assessed",
        "method": "manual",
        "notes": "Not a declared source.",
    })
    assert missing_source.status_code == 404

    mismatched_evidence = client.post("/v1/evidence-assessments", json={
        "knowledge_id": record["id"],
        "source_id": "syndicated",
        "evidence_id": "evidence-1",
        "stance": "supports",
        "status": "assessed",
        "method": "manual",
        "notes": "Evidence belongs to a different source.",
    })
    assert mismatched_evidence.status_code == 422


def test_evidence_assessments_are_append_only_and_survive_backup(tmp_path):
    database = tmp_path / "assessment.sqlite3"
    backup = tmp_path / "assessment-backup.sqlite3"
    client = TestClient(create_app(str(database)))
    record = client.post("/v1/knowledge", json=_knowledge_payload()).json()
    response = client.post("/v1/evidence-assessments", json={
        "knowledge_id": record["id"],
        "source_id": "primary",
        "evidence_id": "evidence-1",
        "stance": "supports",
        "status": "review_required",
        "method": "cross_check",
        "notes": "Independent verification is still required.",
    })
    assert response.status_code == 201
    assessment = response.json()
    assert assessment["actor"] == "system"
    assert assessment["status"] == "review_required"

    listed = client.get(
        "/v1/evidence-assessments",
        params={"knowledge_id": record["id"]},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [assessment["id"]]

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE evidence_assessments SET payload = '{}' WHERE id = ?",
                (assessment["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM evidence_assessments WHERE id = ?",
                (assessment["id"],),
            )

    store = KnowledgeStore(database)
    store.backup(backup)
    assert store.verify_backup(backup) == 1
    restored = TestClient(create_app(str(backup)))
    assert restored.get(
        "/v1/evidence-assessments",
        params={"knowledge_id": record["id"]},
    ).json()[0]["id"] == assessment["id"]
