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
