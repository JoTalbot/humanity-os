from fastapi.testclient import TestClient

from humanity_os.app import create_app


def test_create_read_update_list_and_delete_knowledge(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    payload = {
        "kind": "observation",
        "title": "First note",
        "content": "A user-owned knowledge record.",
    }
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


def test_invalid_cursor_is_rejected(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    assert client.get("/v1/knowledge?cursor=not-a-valid-cursor").status_code == 400


def test_search_and_json_export(tmp_path):
    client = TestClient(create_app(str(tmp_path / "test.sqlite3")))
    client.post(
        "/v1/knowledge",
        json={"kind": "claim", "title": "Ocean research", "content": "Water samples"},
    )
    client.post(
        "/v1/knowledge",
        json={"kind": "observation", "title": "Garden", "content": "Tomatoes"},
    )
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

    literal_percent = client.get("/v1/knowledge?q=%25").json()["items"]
    assert len(literal_percent) == 3
