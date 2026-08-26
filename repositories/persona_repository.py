from database.db import get_connection


PERMANENT_PEOPLE = [
    "Papá",
    "Mamá",
    "Fernando",
    "Nayeli",
    "Angel",
]


class PersonaRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS personas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    permanente INTEGER NOT NULL DEFAULT 1
                        CHECK (permanente IN (0, 1))
                )
                """
            )

    def create_permanent_people(self):
        inserted = 0

        with get_connection() as connection:
            for name in PERMANENT_PEOPLE:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO personas (
                        nombre,
                        permanente
                    )
                    VALUES (?, 1)
                    """,
                    (name,),
                )

                inserted += cursor.rowcount

        return inserted

    def list_permanent_people(self):
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, nombre, permanente
                FROM personas
                WHERE permanente = 1
                ORDER BY id
                """
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]