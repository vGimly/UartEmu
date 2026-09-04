from lib.api import request


def test_reload_app():
    status, data = request(
        "PUT",
        "/api/reload_app",
    )

    assert status == 200
    assert data["status"] == "ok"
