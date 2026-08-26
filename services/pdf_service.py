import os
import re
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PASSWORD = os.getenv("PDF_PASSWORD")

TRANSACTION_PATTERN = re.compile(
    r"^(?P<date>\d{2}-[A-Za-z]{3})\s+"
    r"(?P<description>.*?)\s+"
    r"(?P<soles>-?[\d,]+\.\d{2})"
    r"(?:\s+(?P<dollars>-?[\d,]+\.\d{2}))?\s*$"
)


class PdfService:

    def __init__(self, password=None):
        self.password = password or PDF_PASSWORD

        if not self.password:
            raise ValueError(
                "Falta PDF_PASSWORD en el archivo .env"
            )

    def extract_text(self, pdf_path):
        """Abre el PDF protegido y extrae su texto."""

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"No existe el PDF: {pdf_path}"
            )

        try:
            reader = PdfReader(
                pdf_path,
                password=self.password,
            )

            pages_text = []

            for page_number, page in enumerate(
                reader.pages,
                start=1,
            ):
                text = page.extract_text(
                    extraction_mode="layout"
                )

                pages_text.append(
                    f"\n===== PÁGINA {page_number} =====\n"
                    f"{text or ''}"
                )

            full_text = "\n".join(pages_text)

            if not full_text.strip():
                raise ValueError(
                    "No se pudo extraer texto del PDF"
                )

            return {
                "text": full_text,
                "page_count": len(reader.pages),
            }

        except FileNotDecryptedError as error:
            raise ValueError(
                "No se pudo abrir el PDF. "
                "Verifica la contraseña."
            ) from error

    def extract_consumptions(self, pdf_path):
        """Extrae consumos de Angel, Nayeli y el seguro."""

        result = self.extract_text(pdf_path)
        text = result["text"]

        angel_text = self._extract_section(
            text,
            "ANGEL QUISPE",
            "NAYELI INGARUCA",
        )

        nayeli_text = self._extract_section(
            text,
            "NAYELI INGARUCA",
            "SUBTOTAL",
        )

        insurance_text = self._extract_section(
            text,
            "OTROS COBROS",
            "SUBTOTAL",
        )

        angel = self._parse_transactions(
            angel_text,
            owner="Angel",
            assignment="PENDIENTE",
        )

        nayeli = self._parse_transactions(
            nayeli_text,
            owner="Nayeli",
            assignment="AUTOMATICA",
        )

        insurance = self._parse_transactions(
            insurance_text,
            owner="Seguro",
            assignment="NO_ASIGNAR",
        )

        return {
            "angel": angel,
            "nayeli": nayeli,
            "insurance": insurance,
            "page_count": result["page_count"],
        }

    def _extract_section(
        self,
        text,
        start_marker,
        end_marker,
    ):
        start = text.find(start_marker)

        if start == -1:
            raise ValueError(
                f"No se encontró la sección: {start_marker}"
            )

        start += len(start_marker)
        end = text.find(end_marker, start)

        if end == -1:
            raise ValueError(
                f"No se encontró el final: {end_marker}"
            )

        return text[start:end]

    def _parse_transactions(
        self,
        section_text,
        owner,
        assignment,
    ):
        transactions = []

        for original_line in section_text.splitlines():
            line = " ".join(original_line.split())

            match = TRANSACTION_PATTERN.match(line)

            if not match:
                continue

            soles = self._to_decimal(
                match.group("soles")
            )

            dollars = self._to_decimal(
                match.group("dollars") or "0.00"
            )

            transactions.append({
                "date": match.group("date"),
                "description": match.group(
                    "description"
                ).strip(),
                "soles": soles,
                "dollars": dollars,
                "owner": owner,
                "assignment": assignment,
            })

        return transactions

    @staticmethod
    def _to_decimal(value):
        return Decimal(
            value.replace(",", "")
        )