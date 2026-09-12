from database.db import get_connection


class MovimientoAsignacionRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    movimientos_asignacion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumo_id INTEGER NOT NULL,
                    persona_id INTEGER NOT NULL,
                    moneda TEXT NOT NULL
                        CHECK (
                            moneda IN (
                                'PEN',
                                'USD'
                            )
                        ),
                    monto_centimos INTEGER NOT NULL
                        CHECK (
                            monto_centimos > 0
                        ),
                    fecha_registro TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (consumo_id)
                        REFERENCES consumos(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                        ON DELETE RESTRICT
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_movimientos_asignacion_consumo
                ON movimientos_asignacion (
                    consumo_id,
                    id
                )
                """
            )

    def add_movement(
        self,
        consumption_id,
        person_id,
        amount_cents,
    ):
        if not isinstance(amount_cents, int):
            raise TypeError(
                "El monto debe expresarse "
                "en centimos enteros"
            )

        if amount_cents <= 0:
            raise ValueError(
                "El monto debe ser mayor "
                "que cero"
            )

        with get_connection() as connection:
            consumption = connection.execute(
                """
                SELECT
                    id,
                    estado_id,
                    monto_soles_centimos,
                    monto_dolares_centimos
                FROM consumos
                WHERE id = ?
                """,
                (consumption_id,),
            ).fetchone()

            if consumption is None:
                raise LookupError(
                    "No existe el consumo"
                )

            person = connection.execute(
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

            if person is None:
                raise LookupError(
                    "No existe la persona"
                )

            available = connection.execute(
                """
                SELECT 1
                FROM personas AS p
                WHERE p.id = ?
                  AND (
                      p.permanente = 1
                      OR EXISTS (
                          SELECT 1
                          FROM estado_personas AS ep
                          WHERE ep.estado_id = ?
                            AND ep.persona_id = p.id
                      )
                  )
                """,
                (
                    person_id,
                    consumption["estado_id"],
                ),
            ).fetchone()

            if available is None:
                raise ValueError(
                    "La persona no esta "
                    "disponible para este "
                    "estado de cuenta"
                )

            currency, total_cents = (
                self._get_currency_and_total(
                    consumption
                )
            )

            assigned_row = connection.execute(
                """
                SELECT
                    COALESCE(
                        SUM(monto_centimos),
                        0
                    ) AS total
                FROM movimientos_asignacion
                WHERE consumo_id = ?
                  AND moneda = ?
                """,
                (
                    consumption_id,
                    currency,
                ),
            ).fetchone()

            pending_cents = (
                total_cents
                - assigned_row["total"]
            )

            if amount_cents > pending_cents:
                raise ValueError(
                    "El monto no puede superar "
                    "el saldo pendiente"
                )

            cursor = connection.execute(
                """
                INSERT INTO movimientos_asignacion (
                    consumo_id,
                    persona_id,
                    moneda,
                    monto_centimos
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    consumption_id,
                    person_id,
                    currency,
                    amount_cents,
                ),
            )

            movement_id = cursor.lastrowid

        return movement_id

    def get_balance(
        self,
        consumption_id,
    ):
        with get_connection() as connection:
            consumption = connection.execute(
                """
                SELECT
                    id,
                    monto_soles_centimos,
                    monto_dolares_centimos
                FROM consumos
                WHERE id = ?
                """,
                (consumption_id,),
            ).fetchone()

            if consumption is None:
                raise LookupError(
                    "No existe el consumo"
                )

            currency, total_cents = (
                self._get_currency_and_total(
                    consumption
                )
            )

            assigned_row = connection.execute(
                """
                SELECT
                    COALESCE(
                        SUM(monto_centimos),
                        0
                    ) AS total
                FROM movimientos_asignacion
                WHERE consumo_id = ?
                  AND moneda = ?
                """,
                (
                    consumption_id,
                    currency,
                ),
            ).fetchone()

        assigned_cents = (
            assigned_row["total"]
        )

        pending_cents = (
            total_cents
            - assigned_cents
        )

        return {
            "currency": currency,
            "total_cents": total_cents,
            "assigned_cents": assigned_cents,
            "pending_cents": pending_cents,
            "completed": pending_cents == 0,
        }

    def list_movements(
        self,
        consumption_id,
    ):
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    ma.id,
                    ma.consumo_id,
                    ma.persona_id,
                    p.nombre AS persona,
                    ma.moneda,
                    ma.monto_centimos,
                    ma.fecha_registro
                FROM movimientos_asignacion AS ma
                INNER JOIN personas AS p
                    ON p.id = ma.persona_id
                WHERE ma.consumo_id = ?
                ORDER BY ma.id
                """,
                (consumption_id,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def list_movements_by_statement(
        self,
        estado_id,
    ):
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    ma.id AS movimiento_id,
                    c.id AS consumo_id,
                    p.id AS persona_id,
                    p.nombre AS persona,
                    c.fecha,
                    c.descripcion,
                    ma.moneda,
                    ma.monto_centimos,
                    ma.fecha_registro,
                    'MOVIMIENTO' AS origen
                FROM movimientos_asignacion AS ma
                INNER JOIN consumos AS c
                    ON c.id = ma.consumo_id
                INNER JOIN personas AS p
                    ON p.id = ma.persona_id
                WHERE c.estado_id = ?

                UNION ALL

                SELECT
                    NULL AS movimiento_id,
                    c.id AS consumo_id,
                    p.id AS persona_id,
                    p.nombre AS persona,
                    c.fecha,
                    c.descripcion,
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
                    END AS monto_centimos,
                    NULL AS fecha_registro,
                    'AUTOMATICA' AS origen
                FROM consumos AS c
                INNER JOIN personas AS p
                    ON p.id = c.persona_id
                WHERE c.estado_id = ?
                  AND c.asignacion = ?
                  AND c.persona_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM movimientos_asignacion AS ma
                      WHERE ma.consumo_id = c.id
                  )

                UNION ALL

                SELECT
                    NULL AS movimiento_id,
                    c.id AS consumo_id,
                    p.id AS persona_id,
                    p.nombre AS persona,
                    c.fecha,
                    c.descripcion,
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
                    END AS monto_centimos,
                    NULL AS fecha_registro,
                    'MANUAL_ANTIGUA' AS origen
                FROM consumos AS c
                INNER JOIN personas AS p
                    ON p.id = c.persona_id
                WHERE c.estado_id = ?
                  AND c.asignacion = ?
                  AND c.persona_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM movimientos_asignacion AS ma
                      WHERE ma.consumo_id = c.id
                  )

                ORDER BY
                    persona,
                    consumo_id,
                    movimiento_id
                """,
                (
                    estado_id,
                    estado_id,
                    "AUTOMATICA",
                    estado_id,
                    "MANUAL",
                ),
            ).fetchall()

        return [
            dict(row)
            for row in rows
            if (
                row["moneda"] is not None
                and row["monto_centimos"] > 0
            )
        ]
    
    def get_distributed_totals(
        self,
        estado_id,
    ):
        movements = (
            self.list_movements_by_statement(
                estado_id
            )
        )

        total_pen_cents = sum(
            movement["monto_centimos"]
            for movement in movements
            if movement["moneda"] == "PEN"
        )

        total_usd_cents = sum(
            movement["monto_centimos"]
            for movement in movements
            if movement["moneda"] == "USD"
        )

        return {
            "PEN": total_pen_cents,
            "USD": total_usd_cents,
        }

    def delete_last_movement(
        self,
        consumption_id,
    ):
        with get_connection() as connection:
            movement = connection.execute(
                """
                SELECT
                    ma.id,
                    ma.consumo_id,
                    ma.persona_id,
                    p.nombre AS persona,
                    ma.moneda,
                    ma.monto_centimos,
                    ma.fecha_registro
                FROM movimientos_asignacion AS ma
                INNER JOIN personas AS p
                    ON p.id = ma.persona_id
                WHERE ma.consumo_id = ?
                ORDER BY ma.id DESC
                LIMIT 1
                """,
                (consumption_id,),
            ).fetchone()

            if movement is None:
                raise LookupError(
                    "El consumo no tiene "
                    "asignaciones para eliminar"
                )

            connection.execute(
                """
                DELETE FROM movimientos_asignacion
                WHERE id = ?
                """,
                (movement["id"],),
            )

        return dict(movement)

    @staticmethod
    def _get_currency_and_total(
        consumption,
    ):
        soles_cents = (
            consumption[
                "monto_soles_centimos"
            ]
        )

        dollars_cents = (
            consumption[
                "monto_dolares_centimos"
            ]
        )

        if (
            soles_cents > 0
            and dollars_cents == 0
        ):
            return "PEN", soles_cents

        if (
            dollars_cents > 0
            and soles_cents == 0
        ):
            return "USD", dollars_cents

        raise ValueError(
            "El consumo debe tener un monto "
            "valido en una sola moneda"
        )