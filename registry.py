import datetime
import logging
import sqlite3
import uuid

from db import get_connection, init_db, now

log = logging.getLogger("uart.registry")

_conn = None


def _db():
    global _conn
    if _conn is None:
        _conn = get_connection()
        init_db(_conn)
    return _conn


def _decorate_client(client):
    if client is None:
        return None

    result = dict(client)
    if result.get("connected") and result.get("connected_at"):
        started = datetime.datetime.fromisoformat(
            result["connected_at"].replace("Z", "+00:00")
        )
        result["session_duration_seconds"] = int(
            (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()
        )
    else:
        result["session_duration_seconds"] = 0
    return result


def list_devices():
    rows = _db().execute(
        """
        SELECT devices.*, COUNT(state.address) AS state_entries
        FROM devices
        LEFT JOIN state ON state.device_id = devices.id
        GROUP BY devices.id
        ORDER BY devices.name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_device(device_id):
    row = _db().execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return dict(row) if row else None


def get_device_by_identity(identity):
    row = _db().execute("SELECT * FROM devices WHERE identity = ?", (identity,)).fetchone()
    return dict(row) if row else None


def create_device(name, protocol="default", description="", identity=None):
    identity = name if identity is None else identity
    ts = now()
    try:
        cur = _db().execute(
            """
            INSERT INTO devices(name, identity, protocol, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, identity, protocol, description, ts, ts),
        )
    except sqlite3.IntegrityError:
        return None
    _db().commit()
    return get_device(cur.lastrowid)


def update_device(device_id, name=None, identity=None, protocol=None, description=None):
    device = get_device(device_id)
    if device is None:
        return None
    name = device["name"] if name is None else name
    identity = device["identity"] if identity is None else identity
    protocol = device["protocol"] if protocol is None else protocol
    description = device["description"] if description is None else description
    try:
        _db().execute(
            """
            UPDATE devices
            SET name = ?, identity = ?, protocol = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (name, identity, protocol, description, now(), device_id),
        )
    except sqlite3.IntegrityError:
        return None
    _db().commit()
    return get_device(device_id)


def delete_device(device_id):
    cur = _db().execute("DELETE FROM devices WHERE id = ?", (device_id,))
    _db().commit()
    return cur.rowcount > 0


def list_clients():
    rows = _db().execute(
        """
        SELECT clients.*, devices.name AS device_name,
               devices.identity AS device_identity_configured,
               devices.protocol AS device_protocol
        FROM clients
        LEFT JOIN devices ON devices.id = clients.device_id
        ORDER BY clients.connected DESC, clients.last_seen DESC
        """
    ).fetchall()
    return [_decorate_client(row) for row in rows]


def get_client(client_key):
    row = _db().execute(
        """
        SELECT clients.*, devices.name AS device_name,
               devices.identity AS device_identity_configured,
               devices.protocol AS device_protocol
        FROM clients
        LEFT JOIN devices ON devices.id = clients.device_id
        WHERE clients.client_key = ?
        """,
        (client_key,),
    ).fetchone()
    return _decorate_client(row)


def create_client(host, port=0, device_id=None):
    client_key = str(uuid.uuid4())
    ts = now()
    _db().execute(
        """
        INSERT INTO clients(client_key, host, port, device_id, connected, first_seen, last_seen)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (client_key, host, port, device_id, ts, ts),
    )
    _db().commit()
    return get_client(client_key)


def record_connect(host, port):
    client_key = str(uuid.uuid4())
    ts = now()
    default_device = _db().execute(
        "SELECT id FROM devices WHERE identity = 'default'"
    ).fetchone()
    device_id = default_device[0] if default_device else None
    _db().execute(
        """
        INSERT INTO clients(
            client_key, host, port, device_id, connected,
            first_seen, connected_at, last_seen
        ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (client_key, host, port, device_id, ts, ts, ts),
    )
    _db().commit()
    return client_key


def record_disconnect(client_key):
    _db().execute(
        "UPDATE clients SET connected = 0, last_seen = ? WHERE client_key = ?",
        (now(), client_key),
    )
    _db().commit()


def identify_client(client_key, identity):
    device = get_device_by_identity(identity)
    if device is None:
        return None
    _db().execute(
        """
        UPDATE clients
        SET device_id = ?, device_identity = ?, last_seen = ?
        WHERE client_key = ?
        """,
        (device["id"], identity, now(), client_key),
    )
    _db().commit()
    return get_client(client_key)


def assign_device(client_key, device_id):
    client = get_client(client_key)
    if client is None:
        return None
    identity = None
    if device_id is not None:
        device = get_device(device_id)
        if device is None:
            return None
        identity = device["identity"]
    _db().execute(
        """
        UPDATE clients
        SET device_id = ?, device_identity = ?, last_seen = ?
        WHERE client_key = ?
        """,
        (device_id, identity, now(), client_key),
    )
    _db().commit()
    return get_client(client_key)


def record_request(client_key):
    _db().execute(
        "UPDATE clients SET requests = requests + 1, last_seen = ? WHERE client_key = ?",
        (now(), client_key),
    )
    _db().commit()


def record_response(client_key):
    _db().execute(
        "UPDATE clients SET responses = responses + 1, last_seen = ? WHERE client_key = ?",
        (now(), client_key),
    )
    _db().commit()


def delete_client(client_key):
    cur = _db().execute("DELETE FROM clients WHERE client_key = ?", (client_key,))
    _db().commit()
    return cur.rowcount > 0


def protocol_for_client(client_key, default="default"):
    row = _db().execute(
        """
        SELECT devices.protocol AS protocol
        FROM clients
        JOIN devices ON devices.id = clients.device_id
        WHERE clients.client_key = ?
        """,
        (client_key,),
    ).fetchone()
    return default if row is None else row["protocol"]
