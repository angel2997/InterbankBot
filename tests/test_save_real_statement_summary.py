import unittest
from decimal import Decimal
from pathlib import Path

from repositories.estado_repository import (
    EstadoRepository,
)
from services.pdf_service import (
    PdfService,
)


PROJECT_DIR = (
    Path(__file__).resolve().parent.parent
)

PDF_FOLDER = (
    PROJECT_DIR
    / "pdf"
)


class SaveRealStatementSummaryTest(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        pdf_files = [
            file
            for file in PDF_FOLDER.iterdir()
            if (
                file.is_file()
                and file.suffix.lower() == ".pdf"
            )
        ]

        if not pdf_files:
            raise FileNotFoundError(
                "No existen archivos PDF "
                "en la carpeta pdf"
            )

        cls.latest_pdf = max(
            pdf_files,
            key=lambda file: (
                file.stat().st_mtime
            ),
        )

        cls.pdf_service = PdfService()
        cls.estado_repository = (
            EstadoRepository()
        )

        cls.estado_repository.create_table()

        cls.estado_id = (
            cls.estado_repository
            .get_id_by_pdf(
                cls.latest_pdf
            )
        )

        extracted = (
            cls.pdf_service.extract_text(
                cls.latest_pdf
            )
        )

        cls.summary = (
            cls.pdf_service
            .extract_statement_summary(
                extracted["text"]
            )
        )

        cls.estado_repository.save_statement_summary(
            estado_id=cls.estado_id,
            payment_month=(
                cls.summary["payment_month"]
            ),
            insurance=(
                cls.summary["insurance"]
            ),
        )

        cls.stored = (
            cls.estado_repository
            .get_statement_summary(
                cls.estado_id
            )
        )

        print()
        print("=" * 60)
        print(
            "RESUMEN GUARDADO EN SQLITE"
        )
        print("=" * 60)

        print(
            "Estado ID:",
            cls.estado_id,
        )

        print(
            "Archivo:",
            cls.latest_pdf.name,
        )

        print(
            "Periodo:",
            cls.stored["periodo"],
        )

        print()

        print(
            "Pago del mes en soles:",
            cls._format_money(
                cls.stored[
                    "pago_mes_soles_centimos"
                ],
                "S/",
            ),
        )

        print(
            "Pago del mes en dólares:",
            cls._format_money(
                cls.stored[
                    "pago_mes_dolares_centimos"
                ],
                "US$",
            ),
        )

        print(
            "Seguro de desgravamen en soles:",
            cls._format_money(
                cls.stored[
                    "seguro_desgravamen_"
                    "soles_centimos"
                ],
                "S/",
            ),
        )

        print(
            "Seguro de desgravamen en dólares:",
            cls._format_money(
                cls.stored[
                    "seguro_desgravamen_"
                    "dolares_centimos"
                ],
                "US$",
            ),
        )

        print("=" * 60)
        print()

    @staticmethod
    def _to_cents(
        amount,
    ):
        return int(
            Decimal(str(amount))
            * Decimal("100")
        )

    def test_saves_payment_month_soles(
        self,
    ):
        expected = self._to_cents(
            self.summary[
                "payment_month"
            ]["soles"]
        )

        self.assertEqual(
            expected,
            self.stored[
                "pago_mes_soles_centimos"
            ],
        )

    def test_saves_payment_month_dollars(
        self,
    ):
        expected = self._to_cents(
            self.summary[
                "payment_month"
            ]["dollars"]
        )

        self.assertEqual(
            expected,
            self.stored[
                "pago_mes_dolares_centimos"
            ],
        )

    def test_saves_insurance_soles(
        self,
    ):
        expected = self._to_cents(
            self.summary[
                "insurance"
            ]["soles"]
        )

        self.assertEqual(
            expected,
            self.stored[
                "seguro_desgravamen_"
                "soles_centimos"
            ],
        )

    def test_saves_insurance_dollars(
        self,
    ):
        expected = self._to_cents(
            self.summary[
                "insurance"
            ]["dollars"]
        )

        self.assertEqual(
            expected,
            self.stored[
                "seguro_desgravamen_"
                "dolares_centimos"
            ],
        )

    def test_keeps_statement_identity(
        self,
    ):
        self.assertEqual(
            self.latest_pdf.name,
            self.stored["nombre_pdf"],
        )

        self.assertEqual(
            self.estado_id,
            self.stored["id"],
        )

    @staticmethod
    def _format_money(
        amount_cents,
        currency_symbol,
    ):
        amount = (
            Decimal(amount_cents)
            / Decimal("100")
        )

        return (
            f"{currency_symbol} "
            f"{amount:,.2f}"
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )