import datetime
import sqlite3

DB_FILENAME = "uart-state.db"


def get_connection(filename=DB_FILENAME):
    conn = sqlite3.connect(filename, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            protocol TEXT NOT NULL DEFAULT 'application',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            host TEXT PRIMARY KEY,
            port INTEGER NOT NULL DEFAULT 0,
            device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
            connected INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
    )

    conn.commit()


def now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
