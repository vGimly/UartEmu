from db import DB_FILENAME, get_connection, init_db


class DeviceState:
    def __init__(self, filename=DB_FILENAME):
        self.db = get_connection(filename)
        init_db(self.db)

    def read(self, device_id, address, default=0):
        row = self.db.execute(
            """
            SELECT value FROM state
            WHERE device_id = ? AND address = ?
            """,
            (device_id, address),
        ).fetchone()

        if row is None:
            return default

        return row[0]

    def write(self, device_id, address, value):
        self.db.execute(
            """
            INSERT INTO state(device_id, address, value)
            VALUES (?, ?, ?)
            ON CONFLICT(device_id, address)
            DO UPDATE SET value = excluded.value
            """,
            (device_id, address, value),
        )

        self.db.commit()

    def dump(self, device_id):
        rows = self.db.execute(
            """
            SELECT address, value FROM state
            WHERE device_id = ?
            ORDER BY address
            """,
            (device_id,),
        ).fetchall()

        return {"0x%02x" % row[0]: row[1] for row in rows}

    def clear(self, device_id):
        self.db.execute(
            "DELETE FROM state WHERE device_id = ?",
            (device_id,),
        )
        self.db.commit()
