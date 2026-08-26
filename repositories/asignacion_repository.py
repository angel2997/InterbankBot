from database.db import get_connection


class AsignacionRepository:

    def prepare_person_relation(self):
        """
        Agrega persona_id a consumos si todavía no existe.
        """

        with get_connection() as connection:
            columns = connection.execute(
                "PRAGMA table_info(consumos)"
            ).fetchall()

            column_names = {
                column["name"]
                for column in columns
            }

            if "persona_id" not in column_names:
                connection.execute(
                    """
                    ALTER TABLE consumos
                    ADD COLUMN persona_id INTEGER
                    REFERENCES personas(id)
                    """
                )

    def assign_nayeli_automatically(self, estado_id):
        """
        Asigna todos los consumos cuyo titular es Nayeli
        a la persona permanente Nayeli.
        """

        with get_connection() as connection:
            nayeli = connection.execute(
                """
                SELECT id
                FROM personas
                WHERE nombre = ?
                  AND permanente = 1
                """,
                ("Nayeli",),
            ).fetchone()

            if nayeli is None:
                raise LookupError(
                    "No existe la persona permanente Nayeli"
                )

            cursor = connection.execute(
                """
                UPDATE consumos
                SET persona_id = ?,
                    persona_asignada = ?,
                    asignacion = ?
                WHERE estado_id = ?
                  AND titular = ?
                  AND persona_id IS NULL
                """,
                (
                    nayeli["id"],
                    "Nayeli",
                    "AUTOMATICA",
                    estado_id,
                    "Nayeli",
                ),
            )

        return cursor.rowcount

    def count_nayeli_assignments(self, estado_id):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM consumos AS c
                INNER JOIN personas AS p
                    ON p.id = c.persona_id
                WHERE c.estado_id = ?
                  AND p.nombre = ?
                """,
                (
                    estado_id,
                    "Nayeli",
                ),
            ).fetchone()

        return row["total"]