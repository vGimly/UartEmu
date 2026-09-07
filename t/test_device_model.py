import sqlite3

from db import get_connection, init_db
from state import DeviceState


def test_clients_are_unique_by_client_key(tmp_path):
    db_file = tmp_path / "state.db"
    conn = get_connection(str(db_file))
    init_db(conn)

    default = conn.execute(
        "SELECT id FROM devices WHERE identity = 'default'"
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO clients(
            client_key, host, port, device_id, connected,
            first_seen, last_seen
        ) VALUES (?, ?, ?, ?, 1, 't', 't')
        """,
        ("client-a", "10.0.0.1", 10001, default),
    )
    conn.execute(
        """
        INSERT INTO clients(
            client_key, host, port, device_id, connected,
            first_seen, last_seen
        ) VALUES (?, ?, ?, ?, 1, 't', 't')
        """,
        ("client-b", "10.0.0.1", 10002, default),
    )
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 2


def test_state_is_isolated_by_device(tmp_path):
    db_file = tmp_path / "state.db"
    state = DeviceState(str(db_file))
    conn = sqlite3.connect(str(db_file))
    init_db(conn)

    conn.execute(
        "INSERT INTO devices(name, identity, protocol, description, created_at, updated_at) "
        "VALUES ('device-a', 'device-a', 'default', '', 't', 't')"
    )
    device_a = conn.execute(
        "SELECT id FROM devices WHERE identity = 'device-a'"
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO devices(name, identity, protocol, description, created_at, updated_at) "
        "VALUES ('device-b', 'device-b', 'default', '', 't', 't')"
    )
    device_b = conn.execute(
        "SELECT id FROM devices WHERE identity = 'device-b'"
    ).fetchone()[0]
    conn.commit()

    state.write(device_a, 2, 123)
    state.write(device_b, 2, -456)

    assert state.read(device_a, 2) == 123
    assert state.read(device_b, 2) == -456
    assert state.dump(device_a) == {"0x02": 123}
    assert state.dump(device_b) == {"0x02": -456}
