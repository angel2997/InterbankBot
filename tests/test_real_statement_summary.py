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
            cls.summary[
                "payment_month"
            ]["soles"],
        )

        print(
            "Pago del mes en dólares:",
            cls.summary[
                "payment_month"
            ]["dollars"],
        )

        print(
            "Seguro en soles:",
            cls.summary[
                "insurance"
            ]["soles"],
        )

        print(
            "Seguro en dólares:",
            cls.summary[
                "insurance"
            ]["dollars"],
        )

        print("=" * 60)
        print()

    def test_extracts_payment_month_soles(
        self,
    ):
        self.assertEqual(
            Decimal("1856.57"),
            self.summary[
                "payment_month"
            ]["soles"],
        )

    def test_extracts_payment_month_dollars(
        self,
    ):
        self.assertEqual(
            Decimal("0.00"),
            self.summary[
                "payment_month"
            ]["dollars"],
        )

    def test_extracts_insurance_soles(
        self,
    ):
        self.assertEqual(
            Decimal("12.62"),
            self.summary[
                "insurance"
            ]["soles"],
        )

    def test_extracts_insurance_dollars(
        self,
    ):
        self.assertEqual(
            Decimal("0.00"),
            self.summary[
                "insurance"
            ]["dollars"],
        )

    def test_payment_matches_subtotal_and_insurance(
        self,
    ):
        payment_soles = (
            self.summary[
                "payment_month"
            ]["soles"]
        )

        insurance_soles = (
            self.summary[
                "insurance"
            ]["soles"]
        )

        consumption_subtotal_soles = (
            payment_soles
            - insurance_soles
        )

        self.assertEqual(
            Decimal("1843.95"),
            consumption_subtotal_soles,
        )

    def test_values_are_non_negative(
        self,
    ):
        values = (
            self.summary[
                "payment_month"
            ]["soles"],
            self.summary[
                "payment_month"
            ]["dollars"],
            self.summary[
                "insurance"
            ]["soles"],
            self.summary[
                "insurance"
            ]["dollars"],
        )

        for value in values:
            with self.subTest(
                value=value
            ):
                self.assertGreaterEqual(
                    value,
                    Decimal("0.00"),
                )

    def test_pdf_has_pages(
        self,
    ):
        self.assertGreater(
            self.page_count,
            0,
        )

    def test_selected_file_is_pdf(
        self,
    ):
        self.assertEqual(
            ".pdf",
            self.latest_pdf.suffix.lower(),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )