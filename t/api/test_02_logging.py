from lib.api import request


def test_logging_off():
    status, data = request(
        "PUT",
        "/api/logging",
        {"traffic": False},
    )

    assert status == 200
    assert data["traffic"] is False

    status, data = request(
        "GET",
        "/api/logging",
    )

    assert status == 200
    assert data["traffic"] is False


def test_logging_on():
    status, data = request(
        "PUT",
        "/api/logging",
        {"traffic": True},
    )

    assert status == 200
    assert data["traffic"] is True
