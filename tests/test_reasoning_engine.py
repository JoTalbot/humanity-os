import sqlite3
from itertools import pairwise

import pytest
from fastapi.testclient import TestClient as _TestClient

from humanity_os.app import create_app as _create_app
from humanity_os.store import KnowledgeStore


def _record(client, title, scope="test-scope", temporal_scope="2026"):
    created = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": title,
        "content": "A source-backed proposition.",
        "sources": [{
            "id": "source-1",
            "uri": "https://example.org/" + title.lower().replace(" ", "-"),
            "title": "Primary source",
            "publisher": "Example publisher",
        }],
        "evidence": [{
            "id": "evidence-1",
            "source_id": "source-1",
            "relation": "supports",
            "excerpt": "A short supporting excerpt.",
            "locator": "page 2",
        }],
    })
    assert created.status_code == 201
    return created.json()


def _claim(client, record, statement, scope="test-scope", temporal_scope="2026"):
    response = client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": statement,
        "scope": scope,
        "temporal_scope": temporal_scope,
        "evidence_ids": ["evidence-1"],
    })
    assert response.status_code == 201
    return response.json()



# Existing API behavior tests explicitly opt into the isolated, loopback-only
# anonymous mode. Production create_app() remains authenticated by default.
def create_app(*args, **kwargs):
    kwargs["allow_unauthenticated_local"] = True
    return _create_app(*args, **kwargs)


class TestClient(_TestClient):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(app, **kwargs)


def test_reasoning_run_traverses_typed_edges_and_returns_evidence_paths(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning.sqlite3")))
    first_record = _record(client, "First")
    second_record = _record(client, "Second")
    first = _claim(client, first_record, "First proposition")
    second = _claim(client, second_record, "Second proposition")
    edge = client.post("/v1/claim-relations", json={
        "source_claim_id": first["id"],
        "target_claim_id": second["id"],
        "relation": "supports",
        "rationale": "The first proposition supports the second.",
    })
    assert edge.status_code == 201

    result = client.post("/v1/reasoning/runs", json={
        "query": "Explain the proposition",
        "root_claim_id": first["id"],
        "max_depth": 2,
        "max_nodes": 10,
    })
    assert result.status_code == 201
    run = result.json()
    assert {item["id"] for item in run["claims"]} == {first["id"], second["id"]}
    assert run["paths"] == [[first["id"]], [first["id"], second["id"]]]
    assert run["relations"][0]["id"] == edge.json()["id"]
    assert {item["source_id"] for item in run["evidence"]} == {"source-1"}
    assert run["evidence"][0]["locator"] == "page 2"
    assert "This is a graph explanation, not a proof of truth." in run["limitations"]
    assert client.get("/v1/reasoning/runs/" + run["id"]).json() == run


def test_reasoning_respects_exact_scope_and_temporal_filters(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-filters.sqlite3")))
    record = _record(client, "Filter root")
    other_record = _record(client, "Other scope")
    root = _claim(client, record, "Root proposition")
    wrong_scope = _claim(client, other_record, "Other proposition", scope="different")
    client.post("/v1/claim-relations", json={
        "source_claim_id": root["id"],
        "target_claim_id": wrong_scope["id"],
        "relation": "supports",
        "rationale": "A relation crossing scopes.",
    })

    result = client.post("/v1/reasoning/runs", json={
        "query": "Only the requested scope",
        "root_claim_id": root["id"],
        "scope": "test-scope",
        "temporal_scope": "2026",
    })
    assert result.status_code == 201
    assert [item["id"] for item in result.json()["claims"]] == [root["id"]]

    invalid_root = client.post("/v1/reasoning/runs", json={
        "query": "Mismatched root",
        "root_claim_id": root["id"],
        "temporal_scope": "2025",
    })
    assert invalid_root.status_code == 422


def test_reasoning_depth_and_node_limits_are_enforced(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-bounds.sqlite3")))
    record = _record(client, "Bounded")
    claims = [_claim(client, record, f"Claim {index}") for index in range(4)]
    for source, target in pairwise(claims):
        response = client.post("/v1/claim-relations", json={
            "source_claim_id": source["id"],
            "target_claim_id": target["id"],
            "relation": "depends_on",
            "rationale": "A bounded dependency edge.",
        })
        assert response.status_code == 201

    result = client.post("/v1/reasoning/runs", json={
        "query": "Bound traversal",
        "root_claim_id": claims[0]["id"],
        "max_depth": 1,
        "max_nodes": 2,
    })
    assert result.status_code == 201
    assert len(result.json()["claims"]) == 2
    assert len(result.json()["paths"]) == 2
    assert any("node limit was reached" in item for item in result.json()["limitations"])


def test_only_explicit_contradiction_edges_are_reported_as_candidates(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-conflicts.sqlite3")))
    record = _record(client, "Conflict")
    first = _claim(client, record, "A proposition")
    second = _claim(client, record, "An opposing proposition")
    edge = client.post("/v1/claim-relations", json={
        "source_claim_id": first["id"],
        "target_claim_id": second["id"],
        "relation": "contradicts",
        "rationale": "A reviewer marked these as potentially inconsistent.",
    }).json()

    result = client.post("/v1/reasoning/runs", json={
        "query": "Inspect contradiction",
        "root_claim_id": first["id"],
    })
    assert result.status_code == 201
    assert result.json()["contradiction_candidates"] == [edge["id"]]


def test_reasoning_runs_are_append_only_and_backup_verified(tmp_path):
    database = tmp_path / "reasoning.sqlite3"
    backup = tmp_path / "reasoning-backup.sqlite3"
    client = TestClient(create_app(str(database)))
    record = _record(client, "Immutable run")
    claim = _claim(client, record, "A proposition")
    run = client.post("/v1/reasoning/runs", json={
        "query": "Record an explanation",
        "root_claim_id": claim["id"],
    }).json()

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE reasoning_runs SET payload = '{}' WHERE id = ?", (run["id"],)
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM reasoning_runs WHERE id = ?", (run["id"],))

    store = KnowledgeStore(database)
    store.backup(backup)
    assert store.verify_backup(backup) == 1
    restored = TestClient(create_app(str(backup)))
    assert restored.get("/v1/reasoning/runs/" + run["id"]).status_code == 200


def test_reasoning_rejects_missing_root_and_oversized_limits(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-validation.sqlite3")))
    missing = client.post("/v1/reasoning/runs", json={
        "query": "Missing root",
        "root_claim_id": "absent",
    })
    assert missing.status_code == 404
    oversized = client.post("/v1/reasoning/runs", json={
        "query": "Too deep",
        "root_claim_id": "absent",
        "max_depth": 99,
    })
    assert oversized.status_code == 422


def test_reasoning_run_carries_latest_human_evidence_assessment(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-assessments.sqlite3")))
    record = _record(client, "Assessed evidence")
    claim = _claim(client, record, "A proposition with reviewed evidence")

    first = client.post("/v1/evidence-assessments", json={
        "knowledge_id": record["id"],
        "source_id": "source-1",
        "evidence_id": "evidence-1",
        "stance": "supports",
        "status": "review_required",
        "method": "automated_triage",
        "notes": "Automated triage found a possible supporting passage; human review remains required.",
    })
    assert first.status_code == 201
    second = client.post("/v1/evidence-assessments", json={
        "knowledge_id": record["id"],
        "source_id": "source-1",
        "evidence_id": "evidence-1",
        "stance": "refutes",
        "status": "assessed",
        "method": "manual",
        "notes": "Manual review found the excerpt does not support the proposition.",
    })
    assert second.status_code == 201

    result = client.post("/v1/reasoning/runs", json={
        "query": "Explain the assessed proposition",
        "root_claim_id": claim["id"],
    })
    assert result.status_code == 201
    evidence = result.json()["evidence"]
    assert len(evidence) == 1
    assert evidence[0]["assessments"] == [second.json()]
    assert evidence[0]["assessments"][0]["stance"] == "refutes"
    assert evidence[0]["assessments"][0]["status"] == "assessed"


def test_reasoning_run_includes_bounded_source_independence_report(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-independence.sqlite3")))
    record = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Dependent publications",
        "content": "Two publications repeat the same upstream source.",
        "sources": [
            {"id": "primary", "uri": "https://example.org/original", "source_type": "primary"},
            {"id": "copy-a", "uri": "https://example.net/reprint-a", "derived_from_source_ids": ["primary"]},
            {"id": "copy-b", "uri": "https://example.com/reprint-b", "derived_from_source_ids": ["primary"]},
        ],
        "evidence": [
            {"id": "evidence-a", "source_id": "copy-a", "relation": "supports", "excerpt": "Repeated text A"},
            {"id": "evidence-b", "source_id": "copy-b", "relation": "supports", "excerpt": "Repeated text B"},
        ],
    })
    assert record.status_code == 201
    claim = client.post("/v1/claims", json={
        "knowledge_id": record.json()["id"],
        "statement": "The publications share an upstream source.",
        "evidence_ids": ["evidence-a", "evidence-b"],
    })
    assert claim.status_code == 201

    result = client.post("/v1/reasoning/runs", json={
        "query": "Inspect evidence dependence",
        "root_claim_id": claim.json()["id"],
    })

    assert result.status_code == 201
    report = result.json()["evidence_independence"]
    assert report["knowledge_ids"] == [record.json()["id"]]
    assert len(report["dependent_clusters"]) == 1
    assert report["dependent_clusters"][0]["root_source_ids"] == ["primary"]
    assert set(report["dependent_clusters"][0]["member_source_ids"]) == {
        "primary", "copy-a", "copy-b"
    }
    statuses = {item["source_id"]: item["independence_status"] for item in report["sources"]}
    assert statuses["copy-a"] == "derived_dependency"
    assert statuses["copy-b"] == "derived_dependency"
    assert statuses["primary"] == "unknown"


def test_reasoning_comparison_profiles_evidence_without_truth_ranking(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-comparison-profiles.sqlite3")))
    record = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Competing hypotheses evidence",
        "content": "Two hypotheses reference overlapping evidence.",
        "sources": [
            {"id": "source-1", "uri": "https://example.org/shared", "title": "Shared source"},
            {"id": "source-2", "uri": "https://example.net/unique", "title": "Additional source"},
        ],
        "evidence": [
            {"id": "evidence-1", "source_id": "source-1", "relation": "supports", "excerpt": "Shared evidence"},
            {"id": "evidence-2", "source_id": "source-2", "relation": "supports", "excerpt": "Additional evidence"},
        ],
    })
    assert record.status_code == 201
    first = client.post("/v1/claims", json={
        "knowledge_id": record.json()["id"],
        "statement": "Hypothesis A",
        "evidence_ids": ["evidence-1"],
    })
    second = client.post("/v1/claims", json={
        "knowledge_id": record.json()["id"],
        "statement": "Hypothesis B",
        "evidence_ids": ["evidence-1", "evidence-2"],
    })
    assert first.status_code == second.status_code == 201
    for claim, classification in [
        (first.json(), "assumption"),
        (second.json(), "hypothesis"),
    ]:
        assessment = client.post(
            "/v1/claims/" + claim["id"] + "/assessments",
            json={"classification": classification,
                "rationale": "Owner classification for the comparison fixture.",
            },
        )
        assert assessment.status_code == 201
    for evidence_id, source_id, stance, status in [
        ("evidence-1", "source-1", "supports", "assessed"),
        ("evidence-2", "source-2", "refutes", "review_required"),
    ]:
        response = client.post("/v1/evidence-assessments", json={
            "knowledge_id": record.json()["id"],
            "source_id": source_id,
            "evidence_id": evidence_id,
            "stance": stance,
            "status": status,
            "method": "manual" if status == "assessed" else "automated_triage",
            "notes": "Recorded evidence review state for comparison.",
        })
        assert response.status_code == 201

    comparison = client.post("/v1/reasoning/compare", json={
        "query": "Compare the competing hypotheses",
        "root_claim_ids": [first.json()["id"], second.json()["id"]],
    })

    assert comparison.status_code == 201
    body = comparison.json()
    shared = record.json()["id"] + ":evidence-1"
    unique = record.json()["id"] + ":evidence-2"
    assert body["shared_evidence_ids"] == [shared]
    assert body["unique_evidence_ids"][first.json()["id"]] == []
    assert body["unique_evidence_ids"][second.json()["id"]] == [unique]
    profile_a = body["evidence_profiles"][first.json()["id"]]
    profile_b = body["evidence_profiles"][second.json()["id"]]
    assert profile_a["claim_classifications"] == {"assumption": 1}
    assert profile_b["claim_classifications"] == {"hypothesis": 1}
    assert profile_a["assessed_evidence_link_count"] == 1
    assert profile_a["review_required_evidence_link_count"] == 0
    assert profile_b["assessed_evidence_link_count"] == 1
    assert profile_b["review_required_evidence_link_count"] == 1
    assert profile_b["evidence_stance_counts"] == {"refutes": 1, "supports": 1}
    assert "ranking" in body["limitations"][0]
    assert "correctness" in body["limitations"][1]


def test_reasoning_detects_structured_opposite_polarity_candidates(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-structured-contradictions.sqlite3")))
    record_a = _record(client, "Affirmed structured claim")
    record_b = _record(client, "Negated structured claim")
    first = client.post("/v1/claims", json={
        "knowledge_id": record_a["id"],
        "statement": "The service is available.",
        "subject": "Service",
        "predicate": "available",
        "object": "region A",
        "polarity": "affirmed",
        "scope": "region A",
        "temporal_scope": "2026-Q4",
        "evidence_ids": ["evidence-1"],
    })
    second = client.post("/v1/claims", json={
        "knowledge_id": record_b["id"],
        "statement": "The service is not available.",
        "subject": " service ",
        "predicate": "AVAILABLE",
        "object": "REGION A",
        "polarity": "negated",
        "scope": "region A",
        "temporal_scope": "2026-Q4",
        "evidence_ids": ["evidence-1"],
    })
    assert first.status_code == second.status_code == 201
    edge = client.post("/v1/claim-relations", json={
        "source_claim_id": first.json()["id"],
        "target_claim_id": second.json()["id"],
        "relation": "supports",
        "rationale": "Connect both propositions for comparison.",
    })
    assert edge.status_code == 201

    result = client.post("/v1/reasoning/runs", json={
        "query": "Inspect structured polarity",
        "root_claim_id": first.json()["id"],
        "max_depth": 1,
    })

    assert result.status_code == 201
    candidates = result.json()["potential_contradictions"]
    assert len(candidates) == 1
    assert candidates[0]["left_claim_id"] == first.json()["id"]
    assert candidates[0]["right_claim_id"] == second.json()["id"]
    assert candidates[0]["basis"] == "exact_structured_match_opposite_polarity"
    assert result.json()["contradiction_candidates"] == []
