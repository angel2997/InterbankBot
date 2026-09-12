import unittest
from decimal import Decimal
from pathlib import Path

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


class RealStatementSummaryTest(
    unittest.TestCase
):

    @classmethod
    def setUpClass(cls):
        if not PDF_FOLDER.exists():
            raise FileNotFoundError(
                "No existe la carpeta pdf"
            )

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

        extracted = (
            cls.pdf_service
            .extract_text(
                cls.latest_pdf
            )
        )

        cls.summary = (
            cls.pdf_service
            .extract_statement_summary(
                extracted["text"]
            )
        )

        cls.page_count = (
            extracted["page_count"]
        )

        print()
        print("=" * 60)
        print(
            "RESUMEN EXTRAÍDO "
            "DEL PDF REAL"
        )
        print("=" * 60)

        print(
            "Archivo:",
            cls.latest_pdf.name,
        )

        print(
            "Cantidad de páginas:",
            cls.page_count,
        )

        print()

        print(
            "Pago del mes en soles:",
            cls._format_money(
                cls.summary[
                    "payment_month"
                ]["soles"],
                "S/",
            ),
        )

        print(
            "Pago del mes en dólares:",
            cls._format_money(
                cls.summary[
                    "payment_month"
                ]["dollars"],
                "US$",
            ),
        )

        print(
            "Seguro de desgravamen "
            "en soles:",
            cls._format_money(
                cls.summary[
                    "insurance"
                ]["soles"],
                "S/",
            ),
        )

        print(
            "Seguro de desgravamen "
            "en dólares:",
            cls._format_money(
                cls.summary[
                    "insurance"
                ]["dollars"],
                "US$",
            ),
        )

        print("=" * 60)
        print()

    @staticmethod
    def _format_money(
        amount,
        currency_symbol,
    ):
        return (
            f"{currency_symbol} "
            f"{amount:,.2f}"
        )

    def test_selected_file_exists(
        self,
    ):
        self.assertTrue(
            self.latest_pdf.exists()
        )

        self.assertTrue(
            self.latest_pdf.is_file()
        )

    def test_selected_file_is_pdf(
        self,
    ):
        self.assertEqual(
            ".pdf",
            self.latest_pdf.suffix.lower(),
        )

    def test_pdf_has_pages(
        self,
    ):
        self.assertGreater(
            self.page_count,
            0,
        )

    def test_summary_contains_payment_month(
        self,
    ):
        self.assertIn(
            "payment_month",
            self.summary,
        )

        payment = self.summary[
            "payment_month"
        ]

        self.assertIn(
            "soles",
            payment,
        )

        self.assertIn(
            "dollars",
            payment,
        )

    def test_summary_contains_insurance(
        self,
    ):
        self.assertIn(
            "insurance",
            self.summary,
        )

        insurance = self.summary[
            "insurance"
        ]

        self.assertIn(
            "soles",
            insurance,
        )

        self.assertIn(
            "dollars",
            insurance,
        )

    def test_payment_values_are_decimal(
        self,
    ):
        payment = self.summary[
            "payment_month"
        ]

        self.assertIsInstance(
            payment["soles"],
            Decimal,
        )

        self.assertIsInstance(
            payment["dollars"],
            Decimal,
        )

    def test_insurance_values_are_decimal(
        self,
    ):
        insurance = self.summary[
            "insurance"
        ]

        self.assertIsInstance(
            insurance["soles"],
            Decimal,
        )

        self.assertIsInstance(
            insurance["dollars"],
            Decimal,
        )

    def test_payment_values_are_non_negative(
        self,
    ):
        payment = self.summary[
            "payment_month"
        ]

        self.assertGreaterEqual(
            payment["soles"],
            Decimal("0.00"),
        )

        self.assertGreaterEqual(
            payment["dollars"],
            Decimal("0.00"),
        )

    def test_insurance_values_are_non_negative(
        self,
    ):
        insurance = self.summary[
            "insurance"
        ]

        self.assertGreaterEqual(
            insurance["soles"],
            Decimal("0.00"),
        )

        self.assertGreaterEqual(
            insurance["dollars"],
            Decimal("0.00"),
        )

    def test_payment_is_not_less_than_insurance(
        self,
    ):
        payment = self.summary[
            "payment_month"
        ]

        insurance = self.summary[
            "insurance"
        ]

        self.assertGreaterEqual(
            payment["soles"],
            insurance["soles"],
        )

        self.assertGreaterEqual(
            payment["dollars"],
            insurance["dollars"],
        )

    def test_payment_has_two_decimal_places(
        self,
    ):
        payment = self.summary[
            "payment_month"
        ]

        decimal_places = Decimal("0.01")

        self.assertEqual(
            payment["soles"],
            payment["soles"].quantize(
                decimal_places
            ),
        )

        self.assertEqual(
            payment["dollars"],
            payment["dollars"].quantize(
                decimal_places
            ),
        )

    def test_insurance_has_two_decimal_places(
        self,
    ):
        insurance = self.summary[
            "insurance"
        ]

        decimal_places = Decimal("0.01")

        self.assertEqual(
            insurance["soles"],
            insurance["soles"].quantize(
                decimal_places
            ),
        )

        self.assertEqual(
            insurance["dollars"],
            insurance["dollars"].quantize(
                decimal_places
            ),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )