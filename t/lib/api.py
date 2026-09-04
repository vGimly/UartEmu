# t/lib/api.py

import json
import urllib.request

API_URL = "http://127.0.0.1:8000"


def request(method, path, data=None):
    body = None

    if data is not None:
        body = json.dumps(data).encode()

    request = urllib.request.Request(
        API_URL + path,
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status, json.loads(
            response.read()
        )
