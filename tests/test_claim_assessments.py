import sqlite3

import pytest
from fastapi.testclient import TestClient

from humanity_os.app import create_app
from humanity_os.store import KnowledgeStore


def _claim(client):
    record = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Reviewed proposition",
        "content": "A proposition awaiting human review.",
    }).json()
    claim = client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": "The reviewed proposition",
    })
    assert claim.status_code == 201
    return claim.json()


def test_claim_assessment_is_explicit_and_append_only(tmp_path):
    database = tmp_path / "claim-assessment.sqlite3"
    client = TestClient(create_app(str(database)))
    claim = _claim(client)

    first = client.post(
        f"/v1/claims/{claim['id']}/assessments",
        json={"classification": "hypothesis", "rationale": "Evidence is incomplete."},
    )
    assert first.status_code == 201
    assert first.json()["classification"] == "hypothesis"

    second = client.post(
        f"/v1/claims/{claim['id']}/assessments",
        json={"classification": "fact", "rationale": "Reviewed against primary records."},
    )
    assert second.status_code == 201
    history = client.get(f"/v1/claims/{claim['id']}/assessments").json()
    assert [item["classification"] for item in history] == ["fact", "hypothesis"]

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE claim_assessments SET payload = '{}' WHERE id = ?",
                (second.json()["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM claim_assessments WHERE id = ?", (second.json()["id"],)
            )


def test_reasoning_includes_latest_human_assessment_without_inference(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claim-assessment-reasoning.sqlite3")))
    claim = _claim(client)

    no_assessment = client.post("/v1/reasoning/runs", json={
        "query": "Explain without a classification",
        "root_claim_id": claim["id"],
    }).json()
    assert no_assessment["claim_assessments"] == []

    client.post(
        f"/v1/claims/{claim['id']}/assessments",
        json={"classification": "assumption", "rationale": "Used provisionally pending review."},
    )
    client.post(
        f"/v1/claims/{claim['id']}/assessments",
        json={"classification": "unknown", "rationale": "Available evidence does not settle it."},
    )

    run = client.post("/v1/reasoning/runs", json={
        "query": "Explain with reviewed epistemic status",
        "root_claim_id": claim["id"],
    }).json()
    assert len(run["claim_assessments"]) == 1
    assert run["claim_assessments"][0]["classification"] == "unknown"
    assert run["claim_assessments"][0]["rationale"] == "Available evidence does not settle it."
    assert any("human assessments" in item for item in run["limitations"])


def test_claim_assessments_are_verified_and_restored_with_backup(tmp_path):
    database = tmp_path / "claim-assessment-backup.sqlite3"
    backup = tmp_path / "claim-assessment-backup-copy.sqlite3"
    client = TestClient(create_app(str(database)))
    claim = _claim(client)
    assessment = client.post(
        f"/v1/claims/{claim['id']}/assessments",
        json={"classification": "fact", "rationale": "Owner reviewed the source."},
    ).json()

    store = KnowledgeStore(database)
    store.backup(backup)
    assert store.verify_backup(backup) == 1
    restored = TestClient(create_app(str(backup)))
    history = restored.get(f"/v1/claims/{claim['id']}/assessments").json()
    assert history[0]["id"] == assessment["id"]
    assert history[0]["classification"] == "fact"
