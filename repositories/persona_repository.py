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


    def create_statement_people_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS estado_personas (
                    estado_id INTEGER NOT NULL,
                    persona_id INTEGER NOT NULL,
                    PRIMARY KEY (
                        estado_id,
                        persona_id
                    ),
                    FOREIGN KEY (estado_id)
                        REFERENCES estados_procesados(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                        ON DELETE CASCADE
                )
                """
            )


    def find_by_name(
        self,
        person_name,
    ):
        person_name = str(
            person_name
        ).strip()

        if not person_name:
            return None

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    permanente
                FROM personas
                WHERE nombre = ?
                """,
                (person_name,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    def get_by_id(
        self,
        person_id,
    ):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    permanente
                FROM personas
                WHERE id = ?
                """,
                (person_id,),
            ).fetchone()

        if row is None:
            raise LookupError(
                "No existe la persona"
            )

        return dict(row)


    def add_temporary_person(
        self,
        estado_id,
        person_name,
    ):
        person_name = person_name.strip()

        if not person_name:
            raise ValueError(
                "El nombre de la persona es obligatorio"
            )

        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO personas (
                    nombre,
                    permanente
                )
                VALUES (?, 0)
                """,
                (person_name,),
            )

            person = connection.execute(
                """
                SELECT id, nombre
                FROM personas
                WHERE nombre = ?
                """,
                (person_name,),
            ).fetchone()

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO estado_personas (
                    estado_id,
                    persona_id
                )
                VALUES (?, ?)
                """,
                (
                    estado_id,
                    person["id"],
                ),
            )

        return cursor.rowcount == 1

    def list_people_for_statement(
        self,
        estado_id,
    ):
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    nombre,
                    permanente
                FROM personas
                WHERE permanente = 1

                UNION

                SELECT
                    p.id,
                    p.nombre,
                    p.permanente
                FROM personas AS p
                INNER JOIN estado_personas AS ep
                    ON ep.persona_id = p.id
                WHERE ep.estado_id = ?

                ORDER BY nombre
                """,
                (estado_id,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]
