from decimal import Decimal

from database.db import get_connection


class ConsumoRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS consumos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    estado_id INTEGER NOT NULL,
                    fecha TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    monto_soles_centimos INTEGER NOT NULL,
                    monto_dolares_centimos INTEGER NOT NULL,
                    titular TEXT NOT NULL,
                    asignacion TEXT NOT NULL,
                    persona_asignada TEXT,
                    FOREIGN KEY (estado_id)
                        REFERENCES estados_procesados(id)
                        ON DELETE CASCADE
                )
                """
            )

            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                idx_consumo_unico
                ON consumos (
                    estado_id,
                    fecha,
                    descripcion,
                    monto_soles_centimos,
                    monto_dolares_centimos,
                    titular
                )
                """
            )

    def save_many(
        self,
        estado_id,
        consumptions,
    ):
        inserted = 0

        with get_connection() as connection:
            for item in consumptions:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO consumos (
                        estado_id,
                        fecha,
                        descripcion,
                        monto_soles_centimos,
                        monto_dolares_centimos,
                        titular,
                        asignacion,
                        persona_asignada
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        estado_id,
                        item["date"],
                        item["description"],
                        self._to_cents(item["soles"]),
                        self._to_cents(item["dollars"]),
                        item["owner"],
                        item["assignment"],
                        self._initial_person(item),
                    ),
                )

                inserted += cursor.rowcount

        return inserted

    def count_by_statement(self, estado_id):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM consumos
                WHERE estado_id = ?
                """,
                (estado_id,),
            ).fetchone()

        return row["total"]

    @staticmethod
    def _to_cents(amount):
        amount = Decimal(amount)

        return int(
            amount * Decimal("100")
        )

    @staticmethod
    def _initial_person(item):
        if item["assignment"] == "AUTOMATICA":
            return "Nayeli"

        if item["assignment"] == "NO_ASIGNAR":
            return None

        return None