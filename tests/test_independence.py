from fastapi.testclient import TestClient as _TestClient

from humanity_os.app import create_app as _create_app


def _record(client, title, sources):
    response = client.post("/v1/knowledge", json={
        "kind": "document",
        "title": title,
        "content": "Source provenance fixture.",
        "sources": sources,
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


def test_independence_report_groups_declared_sources_and_preserves_unknown(tmp_path):
    client = TestClient(create_app(str(tmp_path / "independence.sqlite3")))
    record = _record(client, "Grouped sources", [
        {"id": "a", "uri": "https://example.org/a", "independence_group_id": "wire-origin"},
        {"id": "b", "uri": "https://example.net/b", "independence_group_id": "wire-origin"},
        {"id": "c", "uri": "https://example.com/c"},
    ])

    response = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": [record["id"]],
    })
    assert response.status_code == 200
    report = response.json()
    assert report["declared_groups"] == [{
        "knowledge_id": record["id"],
        "group_id": "wire-origin",
        "source_keys": ["a", "b"],
    }]
    assert report["unknown_lineage"] == [f'{record["id"]}:c']
    statuses = {item["source_id"]: item["independence_status"] for item in report["sources"]}
    assert statuses == {
        "a": "declared_group",
        "b": "declared_group",
        "c": "unknown",
    }


def test_independence_report_detects_shared_upstream_derivation(tmp_path):
    client = TestClient(create_app(str(tmp_path / "independence-lineage.sqlite3")))
    record = _record(client, "Derived publications", [
        {"id": "primary", "uri": "https://example.org/original", "source_type": "primary"},
        {"id": "copy-a", "uri": "https://example.net/reprint-a", "derived_from_source_ids": ["primary"]},
        {"id": "copy-b", "uri": "https://example.com/reprint-b", "derived_from_source_ids": ["primary"]},
    ])

    response = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": [record["id"]],
    })
    assert response.status_code == 200
    report = response.json()
    assert report["dependent_clusters"] == [{
        "knowledge_id": record["id"],
        "root_source_ids": ["primary"],
        "member_source_ids": ["copy-a", "copy-b", "primary"],
        "explanation": report["dependent_clusters"][0]["explanation"],
    }]
    statuses = {item["source_id"]: item["independence_status"] for item in report["sources"]}
    assert statuses["copy-a"] == "derived_dependency"
    assert statuses["copy-b"] == "derived_dependency"
    assert statuses["primary"] == "unknown"


def test_independence_group_ids_are_scoped_to_each_knowledge_record(tmp_path):
    client = TestClient(create_app(str(tmp_path / "independence-scope.sqlite3")))
    first = _record(client, "First", [
        {"id": "same-local-id", "uri": "https://example.org/first", "independence_group_id": "same-group"},
    ])
    second = _record(client, "Second", [
        {"id": "same-local-id", "uri": "https://example.org/second", "independence_group_id": "same-group"},
    ])

    report = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": [first["id"], second["id"]],
    }).json()
    assert len(report["declared_groups"]) == 2
    assert {item["knowledge_id"] for item in report["declared_groups"]} == {
        first["id"], second["id"]
    }
    assert len(report["sources"]) == 2


def test_independence_analysis_enforces_source_limit_and_lineage_validation(tmp_path):
    client = TestClient(create_app(str(tmp_path / "independence-limits.sqlite3")))
    record = _record(client, "Two sources", [
        {"id": "a", "uri": "https://example.org/a"},
        {"id": "b", "uri": "https://example.org/b"},
    ])
    limited = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": [record["id"]],
        "max_sources": 1,
    })
    assert limited.status_code == 422

    cyclic = client.post("/v1/knowledge", json={
        "kind": "document",
        "title": "Cyclic lineage",
        "content": "Invalid lineage must be rejected.",
        "sources": [
            {"id": "a", "uri": "https://example.org/a", "derived_from_source_ids": ["b"]},
            {"id": "b", "uri": "https://example.org/b", "derived_from_source_ids": ["a"]},
        ],
    })
    assert cyclic.status_code == 422


def test_independence_analysis_rejects_duplicate_and_missing_records(tmp_path):
    client = TestClient(create_app(str(tmp_path / "independence-validation.sqlite3")))
    duplicate = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": ["record-1", "record-1"],
    })
    assert duplicate.status_code == 422
    missing = client.post("/v1/evidence-independence/analyze", json={
        "knowledge_ids": ["missing-record"],
    })
    assert missing.status_code == 404
