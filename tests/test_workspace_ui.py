from fastapi.testclient import TestClient

from humanity_os.app import create_app


def test_workspace_ui_and_assets_are_served_without_unlocking_api(tmp_path):
    client = TestClient(
        create_app(str(tmp_path / "workspace.sqlite3")),
        client=("127.0.0.1", 50000),
    )
    home = client.get("/")
    assert home.status_code == 200
    assert home.headers["cache-control"] == "no-store"
    assert "HUMANITY ONE" in home.text
    assert client.get("/static/styles.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/v1/knowledge").status_code == 401


def test_workspace_ui_and_static_assets_keep_loopback_boundary(tmp_path):
    client = TestClient(
        create_app(str(tmp_path / "workspace.sqlite3")),
        client=("192.0.2.20", 50000),
    )
    assert client.get("/").status_code == 403
    assert client.get("/static/app.js").status_code == 403
    assert client.get("/health").status_code == 403


def test_workspace_ui_contains_no_remote_assets_or_persistent_token_storage(tmp_path):
    client = TestClient(
        create_app(str(tmp_path / "workspace.sqlite3")),
        client=("127.0.0.1", 50000),
    )
    html = client.get("/").text
    script = client.get("/static/app.js").text
    assert "https://" not in html
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert "credentials: \"same-origin\"" in script
    assert "X-CSRF-Token" in script
