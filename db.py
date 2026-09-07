import datetime
import sqlite3
import uuid

DB_FILENAME = "uart-state.db"


def get_connection(filename=DB_FILENAME):
    conn = sqlite3.connect(filename, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _table_columns(conn, table):
    return {
        row[1]
        for row in conn.execute("PRAGMA table_info(%s)" % table)
    }


def _table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone() is not None


def _ensure_devices(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            identity TEXT NOT NULL UNIQUE,
            protocol TEXT NOT NULL DEFAULT 'default',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    columns = _table_columns(conn, "devices")

    if "identity" not in columns:
        conn.execute("ALTER TABLE devices ADD COLUMN identity TEXT")
        conn.execute("UPDATE devices SET identity = name WHERE identity IS NULL")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS devices_identity_idx "
            "ON devices(identity)"
        )

    timestamp = now()
    conn.execute(
        """
        INSERT OR IGNORE INTO devices(
            name, identity, protocol, description, created_at, updated_at
        )
        VALUES (?, ?, 'default', ?, ?, ?)
        """,
        ("default", "default", "Default virtual device", timestamp, timestamp),
    )


def _migrate_state(conn):
    if not _table_exists(conn, "state"):
        conn.execute(
            """
            CREATE TABLE state (
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                address INTEGER NOT NULL,
                value INTEGER NOT NULL,
                PRIMARY KEY (device_id, address)
            )
            """
        )
        return

    columns = _table_columns(conn, "state")

    if "device_id" in columns:
        return

    default_device = conn.execute(
        "SELECT id FROM devices WHERE identity = 'default'"
    ).fetchone()

    conn.execute("ALTER TABLE state RENAME TO state_legacy")
    conn.execute(
        """
        CREATE TABLE state (
            device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
            address INTEGER NOT NULL,
            value INTEGER NOT NULL,
            PRIMARY KEY (device_id, address)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO state(device_id, address, value)
        SELECT ?, address, value FROM state_legacy
        """,
        (default_device[0],),
    )
    conn.execute("DROP TABLE state_legacy")


def _migrate_clients(conn):
    if not _table_exists(conn, "clients"):
        conn.execute(
            """
            CREATE TABLE clients (
                client_key TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 0,
                device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
                device_identity TEXT,
                connected INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                connected_at TEXT,
                last_seen TEXT NOT NULL,
                requests INTEGER NOT NULL DEFAULT 0,
                responses INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        return

    columns = _table_columns(conn, "clients")

    if "client_key" in columns:
        for name, definition in (
            ("device_identity", "TEXT"),
            ("connected_at", "TEXT"),
            ("requests", "INTEGER NOT NULL DEFAULT 0"),
            ("responses", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in columns:
                conn.execute(
                    "ALTER TABLE clients ADD COLUMN %s %s" % (name, definition)
                )
        return

    conn.execute("ALTER TABLE clients RENAME TO clients_legacy")
    conn.execute(
        """
        CREATE TABLE clients (
            client_key TEXT PRIMARY KEY,
            host TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 0,
            device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
            device_identity TEXT,
            connected INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL,
            connected_at TEXT,
            last_seen TEXT NOT NULL,
            requests INTEGER NOT NULL DEFAULT 0,
            responses INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    rows = conn.execute("SELECT * FROM clients_legacy").fetchall()
    for row in rows:
        key = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO clients(
                client_key, host, port, device_id, connected,
                first_seen, last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                row["host"],
                row["port"],
                row["device_id"],
                row["connected"],
                row["first_seen"],
                row["last_seen"],
            ),
        )

    conn.execute("DROP TABLE clients_legacy")


def init_db(conn):
    _ensure_devices(conn)
    _migrate_state(conn)
    _migrate_clients(conn)
    conn.commit()
