import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.estado_repository import (
    EstadoRepository,
)
from services.pdf_service import (
    PdfService,
)


SAMPLE_TEXT = """
OTROS COBROS                                      S/       US$
26-Ago    SEGURO DESGRAVAMEN                      7.10     0.00
SUBTOTAL                                           7.10     0.00

PAGO DEL MES (Suma de subtotales) =             1,741.85 126.58
PAGO MÍNIMO DEL MES =                              108.47  11.88
"""


class StatementSummaryTest(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.original_db_path = (
            database_module.DB_PATH
        )

        database_module.DB_PATH = (
            Path(
                self.temporary_directory.name
            )
            / "test.db"
        )

        self.repository = EstadoRepository()
        self.repository.create_table()

        self._insert_statement()

        self.pdf_service = PdfService(
            password="test-password"
        )

    def tearDown(self):
        database_module.DB_PATH = (
            self.original_db_path
        )

        self.temporary_directory.cleanup()

    def _insert_statement(self):
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO estados_procesados (
                    periodo,
                    hash_archivo,
                    nombre_pdf,
                    fecha_procesado,
                    estado
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "2026-08",
                    "test-hash",
                    "estado-prueba.pdf",
                    "2026-09-11T12:00:00",
                    "PROCESADO",
                ),
            )

    def test_extracts_payment_month(
        self,
    ):
        summary = (
            self.pdf_service
            .extract_statement_summary(
                SAMPLE_TEXT
            )
        )

        payment = summary[
            "payment_month"
        ]

        self.assertEqual(
            Decimal("1741.85"),
            payment["soles"],
        )

        self.assertEqual(
            Decimal("126.58"),
            payment["dollars"],
        )

    def test_extracts_insurance(
        self,
    ):
        summary = (
            self.pdf_service
            .extract_statement_summary(
                SAMPLE_TEXT
            )
        )

        insurance = summary["insurance"]

        self.assertEqual(
            Decimal("7.10"),
            insurance["soles"],
        )

        self.assertEqual(
            Decimal("0.00"),
            insurance["dollars"],
        )

    def test_accepts_insurance_with_de(
        self,
    ):
        text = """
        OTROS COBROS
        26-Ago SEGURO DE DESGRAVAMEN 7.10 0.00
        SUBTOTAL 7.10 0.00

        PAGO DEL MES (Suma de subtotales) = 1,741.85 126.58
        """

        summary = (
            self.pdf_service
            .extract_statement_summary(
                text
            )
        )

        self.assertEqual(
            Decimal("7.10"),
            summary["insurance"]["soles"],
        )

    def test_saves_summary_in_cents(
        self,
    ):
        summary = (
            self.pdf_service
            .extract_statement_summary(
                SAMPLE_TEXT
            )
        )

        saved = (
            self.repository
            .save_statement_summary(
                estado_id=1,
                payment_month=(
                    summary["payment_month"]
                ),
                insurance=(
                    summary["insurance"]
                ),
            )
        )

        stored = (
            self.repository
            .get_statement_summary(
                estado_id=1
            )
        )

        self.assertTrue(saved)

        self.assertEqual(
            174185,
            stored[
                "pago_mes_soles_centimos"
            ],
        )

        self.assertEqual(
            12658,
            stored[
                "pago_mes_dolares_centimos"
            ],
        )

        self.assertEqual(
            710,
            stored[
                "seguro_desgravamen_"
                "soles_centimos"
            ],
        )

        self.assertEqual(
            0,
            stored[
                "seguro_desgravamen_"
                "dolares_centimos"
            ],
        )

    def test_adds_columns_to_existing_table(
        self,
    ):
        with get_connection() as connection:
            columns = connection.execute(
                """
                PRAGMA table_info(
                    estados_procesados
                )
                """
            ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        expected_columns = {
            "pago_mes_soles_centimos",
            "pago_mes_dolares_centimos",
            (
                "seguro_desgravamen_"
                "soles_centimos"
            ),
            (
                "seguro_desgravamen_"
                "dolares_centimos"
            ),
        }

        self.assertTrue(
            expected_columns.issubset(
                column_names
            )
        )

    def test_rejects_missing_payment_month(
        self,
    ):
        text = """
        OTROS COBROS
        26-Ago SEGURO DESGRAVAMEN 7.10 0.00
        SUBTOTAL 7.10 0.00
        """

        with self.assertRaisesRegex(
            ValueError,
            "PAGO DEL MES",
        ):
            (
                self.pdf_service
                .extract_statement_summary(
                    text
                )
            )

    def test_rejects_missing_insurance(
        self,
    ):
        text = """
        PAGO DEL MES = 1,741.85 126.58
        """

        with self.assertRaisesRegex(
            ValueError,
            "seguro de desgravamen",
        ):
            (
                self.pdf_service
                .extract_statement_summary(
                    text
                )
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )
