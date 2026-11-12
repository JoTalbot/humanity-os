from fastapi.testclient import TestClient as _TestClient

from humanity_os.app import create_app as _create_app



# Existing API behavior tests explicitly opt into the isolated, loopback-only
# anonymous mode. Production create_app() remains authenticated by default.
def create_app(*args, **kwargs):
    kwargs["allow_unauthenticated_local"] = True
    return _create_app(*args, **kwargs)


class TestClient(_TestClient):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        super().__init__(app, **kwargs)


def test_reasoning_comparison_includes_independence_metadata(tmp_path):
    client = TestClient(create_app(str(tmp_path / "reasoning-independence.sqlite3")))
    record = client.post("/v1/knowledge", json={
        "kind": "claim",
        "title": "Two views of one source family",
        "content": "Two propositions use publications with declared common origin.",
        "sources": [
            {
                "id": "origin",
                "uri": "https://example.org/original",
                "independence_group_id": "same-origin",
            },
            {
                "id": "reprint",
                "uri": "https://example.net/reprint",
                "independence_group_id": "same-origin",
                "derived_from_source_ids": ["origin"],
            },
        ],
        "evidence": [
            {"id": "e-origin", "source_id": "origin", "relation": "supports"},
            {"id": "e-reprint", "source_id": "reprint", "relation": "supports"},
        ],
    }).json()
    first = client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": "The original publication says X.",
        "evidence_ids": ["e-origin"],
    }).json()
    second = client.post("/v1/claims", json={
        "knowledge_id": record["id"],
        "statement": "A reprint repeats X.",
        "evidence_ids": ["e-reprint"],
    }).json()

    response = client.post("/v1/reasoning/compare", json={
        "query": "Compare source independence",
        "root_claim_ids": [first["id"], second["id"]],
        "max_depth": 0,
    })
    assert response.status_code == 201
    comparison = response.json()
    assert comparison["shared_independence_groups"] == [
        f'{record["id"]}:same-origin'
    ]
    assert comparison["dependent_source_edges"] == [
        f'{record["id"]}:reprint<-origin'
    ]
    assert comparison["unknown_lineage_sources"] == []
    assert any("unknown lineage remains unknown" in item for item in comparison["limitations"])
