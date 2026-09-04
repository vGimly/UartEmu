from lib.api import request


def test_state_dump():
    status, data = request(
        "GET",
        "/api/state",
    )

    assert status == 200
    assert isinstance(data, dict)
