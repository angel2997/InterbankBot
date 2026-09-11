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


    def list_pending_angel_consumptions(
        self,
        estado_id,
    ):
        with get_connection() as connection:
            rows = connection.execute(
                """
                WITH consumos_con_saldo AS (
                    SELECT
                        c.id,
                        c.fecha,
                        c.descripcion,
                        c.monto_soles_centimos,
                        c.monto_dolares_centimos,
                        CASE
                            WHEN
                                c.monto_soles_centimos > 0
                                AND
                                c.monto_dolares_centimos = 0
                            THEN 'PEN'

                            WHEN
                                c.monto_dolares_centimos > 0
                                AND
                                c.monto_soles_centimos = 0
                            THEN 'USD'
                        END AS moneda,
                        CASE
                            WHEN
                                c.monto_soles_centimos > 0
                                AND
                                c.monto_dolares_centimos = 0
                            THEN c.monto_soles_centimos

                            WHEN
                                c.monto_dolares_centimos > 0
                                AND
                                c.monto_soles_centimos = 0
                            THEN c.monto_dolares_centimos

                            ELSE 0
                        END AS total_centimos,
                        COALESCE(
                            SUM(
                                ma.monto_centimos
                            ),
                            0
                        ) AS asignado_centimos
                    FROM consumos AS c
                    LEFT JOIN movimientos_asignacion AS ma
                        ON ma.consumo_id = c.id
                    WHERE c.estado_id = ?
                      AND c.titular = ?
                      AND c.asignacion = ?
                    GROUP BY
                        c.id,
                        c.fecha,
                        c.descripcion,
                        c.monto_soles_centimos,
                        c.monto_dolares_centimos
                )

                SELECT
                    id,
                    fecha,
                    descripcion,
                    monto_soles_centimos,
                    monto_dolares_centimos,
                    moneda,
                    total_centimos,
                    asignado_centimos,
                    (
                        total_centimos
                        - asignado_centimos
                    ) AS pendiente_centimos
                FROM consumos_con_saldo
                WHERE total_centimos > 0
                  AND asignado_centimos
                      < total_centimos
                ORDER BY id
                """,
                (
                    estado_id,
                    "Angel",
                    "PENDIENTE",
                ),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "fecha": row["fecha"],
                "descripcion": row["descripcion"],
                "moneda": row["moneda"],
                "total_centimos": (
                    row["total_centimos"]
                ),
                "asignado_centimos": (
                    row["asignado_centimos"]
                ),
                "pendiente_centimos": (
                    row["pendiente_centimos"]
                ),
                "soles": (
                    row["monto_soles_centimos"]
                    / 100
                ),
                "dolares": (
                    row[
                        "monto_dolares_centimos"
                    ]
                    / 100
                ),
                "saldo_pendiente": (
                    row["pendiente_centimos"]
                    / 100
                ),
            }
            for row in rows
        ]


    def assign_consumption(
        self,
        consumption_id,
        person_name,
    ):
        with get_connection() as connection:
            person = connection.execute(
                """
                SELECT id, nombre
                FROM personas
                WHERE nombre = ?
                """,
                (person_name,),
            ).fetchone()

            if person is None:
                raise LookupError(
                    f"No existe la persona: {person_name}"
                )

            consumption = connection.execute(
                """
                SELECT id
                FROM consumos
                WHERE id = ?
                  AND titular = ?
                  AND asignacion = ?
                  AND persona_id IS NULL
                """,
                (
                    consumption_id,
                    "Angel",
                    "PENDIENTE",
                ),
            ).fetchone()

            if consumption is None:
                raise LookupError(
                    "El consumo no existe o ya fue asignado"
                )

            cursor = connection.execute(
                """
                UPDATE consumos
                SET persona_id = ?,
                    persona_asignada = ?,
                    asignacion = ?
                WHERE id = ?
                  AND persona_id IS NULL
                """,
                (
                    person["id"],
                    person["nombre"],
                    "MANUAL",
                    consumption_id,
                ),
            )

        return cursor.rowcount == 1

    def get_consumption_assignment(
        self,
        consumption_id,
    ):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    c.id,
                    c.descripcion,
                    c.asignacion,
                    p.nombre AS persona
                FROM consumos AS c
                LEFT JOIN personas AS p
                    ON p.id = c.persona_id
                WHERE c.id = ?
                """,
                (consumption_id,),
            ).fetchone()

        if row is None:
            raise LookupError(
                "No existe el consumo"
            )

        return dict(row)