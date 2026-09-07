import logging
import sqlite3

from db import get_connection, init_db, now

log = logging.getLogger("uart.registry")

_conn = None


def _db():
    global _conn

    if _conn is None:
        _conn = get_connection()
        init_db(_conn)

    return _conn


# ---------------------------------------------------------------- devices


def list_devices():
    rows = _db().execute("SELECT * FROM devices ORDER BY name").fetchall()

    return [dict(row) for row in rows]


def get_device(device_id):
    row = _db().execute(
        "SELECT * FROM devices WHERE id = ?",
        (device_id,),
    ).fetchone()

    return dict(row) if row else None


def create_device(name, protocol="application", description=""):
    ts = now()

    try:
        cur = _db().execute(
            """
            INSERT INTO devices(name, protocol, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, protocol, description, ts, ts),
        )
    except sqlite3.IntegrityError:
        return None

    _db().commit()

    return get_device(cur.lastrowid)


def update_device(device_id, name=None, protocol=None, description=None):
    device = get_device(device_id)

    if device is None:
        return None

    name = device["name"] if name is None else name
    protocol = device["protocol"] if protocol is None else protocol
    description = device["description"] if description is None else description

    try:
        _db().execute(
            """
            UPDATE devices
            SET name = ?, protocol = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, protocol, description, now(), device_id),
        )
    except sqlite3.IntegrityError:
        return None

    _db().commit()

    return get_device(device_id)


def delete_device(device_id):
    cur = _db().execute("DELETE FROM devices WHERE id = ?", (device_id,))
    _db().commit()

    return cur.rowcount > 0


# ---------------------------------------------------------------- clients


def list_clients():
    rows = _db().execute(
        "SELECT * FROM clients ORDER BY last_seen DESC"
    ).fetchall()

    return [dict(row) for row in rows]


def get_client(host):
    row = _db().execute(
        "SELECT * FROM clients WHERE host = ?",
        (host,),
    ).fetchone()

    return dict(row) if row else None


def create_client(host, port=0, device_id=None):
    ts = now()

    try:
        _db().execute(
            """
            INSERT INTO clients(host, port, device_id, connected, first_seen, last_seen)
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (host, port, device_id, ts, ts),
        )
    except sqlite3.IntegrityError:
        return None

    _db().commit()

    return get_client(host)


def record_connect(host, port):
    """
    Called by UARTServer whenever a TCP client connects.

    Creates the client record on first sight, or refreshes port /
    connected / last_seen on subsequent reconnects. Any previously
    assigned device_id is preserved.
    """

    ts = now()

    _db().execute(
        """
        INSERT INTO clients(host, port, connected, first_seen, last_seen)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(host)
        DO UPDATE SET port = excluded.port,
                      connected = 1,
                      last_seen = excluded.last_seen
        """,
        (host, port, ts, ts),
    )
    _db().commit()


def record_disconnect(host):
    _db().execute(
        """
        UPDATE clients
        SET connected = 0, last_seen = ?
        WHERE host = ?
        """,
        (now(), host),
    )
    _db().commit()


def assign_device(host, device_id):
    client = get_client(host)

    if client is None:
        return None

    _db().execute(
        "UPDATE clients SET device_id = ? WHERE host = ?",
        (device_id, host),
    )
    _db().commit()

    return get_client(host)


def delete_client(host):
    cur = _db().execute("DELETE FROM clients WHERE host = ?", (host,))
    _db().commit()

    return cur.rowcount > 0


def protocol_for_host(host, default="application"):
    """
    Resolve which protocol module should handle frames from `host`,
    based on the device (if any) assigned to that client.
    """

    row = _db().execute(
        """
        SELECT devices.protocol AS protocol
        FROM clients
        JOIN devices ON devices.id = clients.device_id
        WHERE clients.host = ?
        """,
        (host,),
    ).fetchone()

    if row is None:
        return default

    return row["protocol"]
