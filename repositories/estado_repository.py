import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from database.db import get_connection


class EstadoRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    estados_procesados (
                    id INTEGER
                        PRIMARY KEY AUTOINCREMENT,
                    periodo TEXT,
                    hash_archivo TEXT
                        NOT NULL UNIQUE,
                    nombre_pdf TEXT NOT NULL,
                    fecha_correo TEXT,
                    fecha_procesado TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    pago_mes_soles_centimos
                        INTEGER,
                    pago_mes_dolares_centimos
                        INTEGER,
                    seguro_desgravamen_soles_centimos
                        INTEGER,
                    seguro_desgravamen_dolares_centimos
                        INTEGER
                )
                """
            )

        self.prepare_statement_summary_columns()


    def prepare_statement_summary_columns(
        self,
    ):
        required_columns = {
            "pago_mes_soles_centimos": (
                "INTEGER"
            ),
            "pago_mes_dolares_centimos": (
                "INTEGER"
            ),
            (
                "seguro_desgravamen_"
                "soles_centimos"
            ): "INTEGER",
            (
                "seguro_desgravamen_"
                "dolares_centimos"
            ): "INTEGER",
        }

        with get_connection() as connection:
            columns = connection.execute(
                """
                PRAGMA table_info(
                    estados_procesados
                )
                """
            ).fetchall()

            existing_columns = {
                column["name"]
                for column in columns
            }

            for (
                column_name,
                column_type,
            ) in required_columns.items():
                if (
                    column_name
                    in existing_columns
                ):
                    continue

                connection.execute(
                    (
                        "ALTER TABLE "
                        "estados_procesados "
                        f"ADD COLUMN {column_name} "
                        f"{column_type}"
                    )
                )

    def save_statement_summary(
        self,
        estado_id,
        payment_month,
        insurance,
    ):
        payment_soles_cents = (
            self._to_cents(
                payment_month["soles"]
            )
        )

        payment_dollars_cents = (
            self._to_cents(
                payment_month["dollars"]
            )
        )

        insurance_soles_cents = (
            self._to_cents(
                insurance["soles"]
            )
        )

        insurance_dollars_cents = (
            self._to_cents(
                insurance["dollars"]
            )
        )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE estados_procesados
                SET
                    pago_mes_soles_centimos = ?,
                    pago_mes_dolares_centimos = ?,
                    seguro_desgravamen_soles_centimos = ?,
                    seguro_desgravamen_dolares_centimos = ?
                WHERE id = ?
                """,
                (
                    payment_soles_cents,
                    payment_dollars_cents,
                    insurance_soles_cents,
                    insurance_dollars_cents,
                    estado_id,
                ),
            )

        if cursor.rowcount != 1:
            raise LookupError(
                "No existe el estado de cuenta"
            )

        return True

    def get_statement_summary(
        self,
        estado_id,
    ):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    periodo,
                    nombre_pdf,
                    pago_mes_soles_centimos,
                    pago_mes_dolares_centimos,
                    seguro_desgravamen_soles_centimos,
                    seguro_desgravamen_dolares_centimos
                FROM estados_procesados
                WHERE id = ?
                """,
                (estado_id,),
            ).fetchone()

        if row is None:
            raise LookupError(
                "No existe el estado de cuenta"
            )

        return dict(row)

    @staticmethod
    def _to_cents(
        amount,
    ):
        decimal_amount = Decimal(
            str(amount)
        )

        return int(
            decimal_amount
            * Decimal("100")
        )

    def calculate_hash(self, pdf_path):
        pdf_path = Path(pdf_path)
        sha256 = hashlib.sha256()

        with pdf_path.open("rb") as file:
            for block in iter(
                lambda: file.read(65536),
                b"",
            ):
                sha256.update(block)

        return sha256.hexdigest()

    def is_processed(self, pdf_path):
        file_hash = self.calculate_hash(pdf_path)

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM estados_procesados
                WHERE hash_archivo = ?
                """,
                (file_hash,),
            ).fetchone()

        return row is not None

    def register(
        self,
        pdf_path,
        email_date=None,
        period=None,
        status="DESCARGADO",
    ):
        pdf_path = Path(pdf_path)
        file_hash = self.calculate_hash(pdf_path)

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO estados_procesados (
                    periodo,
                    hash_archivo,
                    nombre_pdf,
                    fecha_correo,
                    fecha_procesado,
                    estado
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    period,
                    file_hash,
                    pdf_path.name,
                    email_date,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    status,
                ),
            )

        return cursor.rowcount == 1

    def get_id_by_pdf(self, pdf_path):
        file_hash = self.calculate_hash(pdf_path)

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM estados_procesados
                WHERE hash_archivo = ?
                """,
                (file_hash,),
            ).fetchone()

        if row is None:
            raise LookupError(
                "El estado de cuenta aún no está registrado"
            )

        return row["id"]

    