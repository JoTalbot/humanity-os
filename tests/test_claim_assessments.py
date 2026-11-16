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


def _source_backed_claim(client, title, uri):
    record = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": title,
        "content": "A proposition with declared evidence.",
        "sources": [{
            "id": "source-1",
            "uri": uri,
            "title": "Declared source",
            "publisher": "Publisher",
        }],
        "evidence": [{
            "id": "evidence-1",
            "source_id": "source-1",
            "relation": "supports",
            "excerpt": "A bounded excerpt.",
        }],
    }).json()
    return client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": title,
        "evidence_ids": ["evidence-1"],
    }).json()


def test_reasoning_comparison_reports_shared_and_unique_claims_and_source_uris(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-comparison.sqlite3")))
    first = _source_backed_claim(client, "Alternative A", "https://example.org/a")
    second = _source_backed_claim(client, "Alternative B", "https://example.org/b")
    common = _source_backed_claim(client, "Shared evidence", "https://example.org/shared")

    for root in (first, second):
        response = client.post("/v1/claim-relations", json={
            "source_claim_id": root["id"],
            "target_claim_id": common["id"],
            "relation": "supports",
            "rationale": "Both alternatives connect to this proposition.",
        })
        assert response.status_code == 201

    compared = client.post("/v1/reasoning/compare", json={
        "query": "Compare two alternative explanations",
        "root_claim_ids": [first["id"], second["id"]],
        "max_depth": 1,
    })
    assert compared.status_code == 201
    result = compared.json()
    assert result["shared_claim_ids"] == [common["id"]]
    assert result["unique_claim_ids"][first["id"]] == [first["id"]]
    assert result["unique_claim_ids"][second["id"]] == [second["id"]]
    assert result["shared_source_uris"] == ["https://example.org/shared"]
    assert result["unique_source_uris"][first["id"]] == ["https://example.org/a"]
    assert result["unique_source_uris"][second["id"]] == ["https://example.org/b"]
    assert len(result["runs"]) == 2
    assert any("not a ranking" in item for item in result["limitations"])


def test_reasoning_comparison_rejects_duplicate_or_missing_roots_without_partial_runs(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-comparison-validation.sqlite3")))
    claim = _claim(client)
    duplicate = client.post("/v1/reasoning/compare", json={
        "query": "Invalid duplicate roots",
        "root_claim_ids": [claim["id"], claim["id"]],
    })
    assert duplicate.status_code == 422
    missing = client.post("/v1/reasoning/compare", json={
        "query": "Invalid missing root",
        "root_claim_ids": [claim["id"], "missing"],
    })
    assert missing.status_code == 404
    runs = client.get("/v1/reasoning/runs/" + "missing")
    assert runs.status_code == 404
