from lib.api import request


def test_logging_get():
    status, data = request("GET", "/api/logging")

    assert status == 200
    assert "traffic" in data
