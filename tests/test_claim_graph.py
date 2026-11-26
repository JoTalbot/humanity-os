import sqlite3

import pytest
from fastapi.testclient import TestClient as _TestClient

from humanity_os.app import create_app as _create_app
from humanity_os.store import KnowledgeStore


def _claim_record(client, title="Source record"):
    response = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": title,
        "content": "A source record containing one atomic proposition.",
        "sources": [{"id": "source-1", "uri": "https://example.org/primary"}],
        "evidence": [{
            "id": "evidence-1",
            "source_id": "source-1",
            "relation": "supports",
            "excerpt": "Evidence excerpt.",
        }],
    })
    assert response.status_code == 201
    return response.json()


def _create_claim(client, knowledge_id, statement):
    return client.post("/v1/claims", json={
        "knowledge_id": knowledge_id,
        "statement": statement,
        "subject": "Test subject",
        "predicate": "has property",
        "object": "value",
        "scope": "within the test fixture",
        "polarity": "affirmed",
        "modality": "asserted",
        "temporal_scope": "2026",
        "evidence_ids": ["evidence-1"],
    })



# Existing API behavior tests explicitly opt into the isolated, loopback-only
# anonymous mode. Production create_app() remains authenticated by default.
def create_app(*args, **kwargs):
    kwargs["allow_unauthenticated_local"] = True
    return _create_app(*args, **kwargs)


class TestClient(_TestClient):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(app, **kwargs)


def test_claim_node_is_atomic_and_grounded_in_existing_knowledge_evidence(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claims.sqlite3")))
    record = _claim_record(client)
    created = _create_claim(client, record["id"], "The subject has the property.")
    assert created.status_code == 201
    claim = created.json()
    assert claim["knowledge_id"] == record["id"]
    assert claim["evidence_ids"] == ["evidence-1"]
    assert claim["polarity"] == "affirmed"
    assert claim["actor"] == "system"
    assert client.get(f"/v1/claims/{claim['id']}").json()["statement"] == claim["statement"]
    assert client.get("/v1/claims", params={"knowledge_id": record["id"]}).json()[0]["id"] == claim["id"]


def test_claim_requires_claim_knowledge_and_declared_evidence(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claim-validation.sqlite3")))
    document = client.post("/v1/knowledge", json={
        "kind": "document", "title": "Not a claim", "content": "Document body"
    }).json()
    not_claim = client.post("/v1/claims", json={
        "knowledge_id": document["id"], "statement": "A proposition"
    })
    assert not_claim.status_code == 422

    record = _claim_record(client)
    missing_evidence = client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": "A proposition",
        "evidence_ids": ["not-declared"],
    })
    assert missing_evidence.status_code == 422

    missing_record = client.post("/v1/claims", json={
        "knowledge_id": "missing",
        "statement": "A proposition",
    })
    assert missing_record.status_code == 404


def test_claim_relations_are_typed_symmetric_for_contradictions_and_deduplicated(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claim-relations.sqlite3")))
    record = _claim_record(client)
    first = _create_claim(client, record["id"], "The system is available.").json()
    second = _create_claim(client, record["id"], "The system is unavailable.").json()

    relation = client.post("/v1/claim-relations", json={
        "source_claim_id": first["id"],
        "target_claim_id": second["id"],
        "relation": "contradicts",
        "rationale": "The propositions cannot both hold in the same scope.",
    })
    assert relation.status_code == 201
    stored = relation.json()
    assert stored["source_claim_id"] == min(first["id"], second["id"])
    assert stored["target_claim_id"] == max(first["id"], second["id"])

    reversed_duplicate = client.post("/v1/claim-relations", json={
        "source_claim_id": second["id"],
        "target_claim_id": first["id"],
        "relation": "contradicts",
        "rationale": "Same undirected contradiction.",
    })
    assert reversed_duplicate.status_code == 409
    assert client.get(
        "/v1/claim-relations", params={"claim_id": first["id"]}
    ).json()[0]["id"] == stored["id"]


def test_claim_relations_require_existing_distinct_claims(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claim-relations.sqlite3")))
    record = _claim_record(client)
    claim = _create_claim(client, record["id"], "A claim.").json()
    self_relation = client.post("/v1/claim-relations", json={
        "source_claim_id": claim["id"],
        "target_claim_id": claim["id"],
        "relation": "supports",
        "rationale": "Invalid self-edge.",
    })
    assert self_relation.status_code == 422

    missing = client.post("/v1/claim-relations", json={
        "source_claim_id": claim["id"],
        "target_claim_id": "missing",
        "relation": "supports",
        "rationale": "Target is absent.",
    })
    assert missing.status_code == 404


def test_claims_and_relations_are_append_only_and_backup_safe(tmp_path):
    database = tmp_path / "claims.sqlite3"
    backup = tmp_path / "claims-backup.sqlite3"
    safety = tmp_path / "claims-safety.sqlite3"
    client = TestClient(create_app(str(database)))
    record = _claim_record(client)
    first = _create_claim(client, record["id"], "Claim one.").json()
    second = _create_claim(client, record["id"], "Claim two.").json()
    edge = client.post("/v1/claim-relations", json={
        "source_claim_id": first["id"],
        "target_claim_id": second["id"],
        "relation": "depends_on",
        "rationale": "Claim two depends on claim one.",
    }).json()

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE claims SET payload = '{}' WHERE id = ?", (first["id"],))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM claims WHERE id = ?", (first["id"],))
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE claim_relations SET payload = '{}' WHERE id = ?", (edge["id"],)
            )

    store = KnowledgeStore(database)
    store.backup(backup)
    assert store.verify_backup(backup) == 1
    restored = TestClient(create_app(str(backup)))
    assert len(restored.get("/v1/claims").json()) == 2
    assert len(restored.get("/v1/claim-relations").json()) == 1
    assert store.restore(backup, safety) == 1
    assert len(TestClient(create_app(str(database))).get("/v1/claims").json()) == 2


def test_claim_graph_prevents_deleting_knowledge_with_claims(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claims.sqlite3")))
    record = _claim_record(client)
    claim = _create_claim(client, record["id"], "A grounded claim.").json()
    assert claim["id"]
    assert client.delete(f"/v1/knowledge/{record['id']}").status_code == 409
    assert client.get(f"/v1/knowledge/{record['id']}").status_code == 200


def test_restore_initializes_claim_graph_schema_from_legacy_backup(tmp_path):
    database = tmp_path / "active.sqlite3"
    backup = tmp_path / "legacy.sqlite3"
    safety = tmp_path / "safety.sqlite3"
    client = TestClient(create_app(str(database)))
    _claim_record(client)
    KnowledgeStore(database).backup(backup)
    with sqlite3.connect(backup) as connection:
        connection.execute("DROP TRIGGER claims_no_update")
        connection.execute("DROP TRIGGER claims_no_delete")
        connection.execute("DROP TRIGGER claim_relations_no_update")
        connection.execute("DROP TRIGGER claim_relations_no_delete")
        connection.execute("DROP TABLE claim_relations")
        connection.execute("DROP TABLE claims")

    assert KnowledgeStore(database).restore(backup, safety) == 1
    restored = TestClient(create_app(str(database)))
    assert restored.get("/v1/claims").status_code == 200
    assert restored.get("/v1/claim-relations").json() == []


def test_claim_dependency_cycles_are_rejected(tmp_path):
    client = TestClient(create_app(str(tmp_path / "claim-cycles.sqlite3")))
    record = _claim_record(client)
    first = _create_claim(client, record["id"], "First proposition.").json()
    second = _create_claim(client, record["id"], "Second proposition.").json()

    forward = client.post("/v1/claim-relations", json={
        "source_claim_id": first["id"],
        "target_claim_id": second["id"],
        "relation": "depends_on",
        "rationale": "First depends on second.",
    })
    assert forward.status_code == 201

    cycle = client.post("/v1/claim-relations", json={
        "source_claim_id": second["id"],
        "target_claim_id": first["id"],
        "relation": "depends_on",
        "rationale": "Would create a dependency cycle.",
    })
    assert cycle.status_code == 422
