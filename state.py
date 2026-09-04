import sqlite3


class DeviceState:
    def __init__(self, filename="uart-state.db"):
        self.db = sqlite3.connect(filename)

        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                address INTEGER PRIMARY KEY,
                value INTEGER NOT NULL
            )
        """
        )

        self.db.commit()

    def read(self, address, default=0):
        row = self.db.execute(
            "SELECT value FROM state WHERE address = ?",
            (address,),
        ).fetchone()

        if row is None:
            return default

        return row[0]

    def write(self, address, value):
        self.db.execute(
            """
            INSERT INTO state(address, value)
            VALUES (?, ?)
            ON CONFLICT(address)
            DO UPDATE SET value = excluded.value
            """,
            (address, value),
        )

        self.db.commit()

    def dump(self):
        rows = self.db.execute(
            "SELECT address, value FROM state ORDER BY address"
        ).fetchall()

        return {"0x%02x" % address: value for address, value in rows}
