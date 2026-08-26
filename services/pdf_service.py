import os
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

PDF_PASSWORD = os.getenv("PDF_PASSWORD")


class PdfService:

    def __init__(self, password=None):
        self.password = password or PDF_PASSWORD

        if not self.password:
            raise ValueError(
                "Falta PDF_PASSWORD en el archivo .env"
            )

    def extract_text(self, pdf_path):
        """
        Abre el PDF protegido y extrae todo su texto.
        """

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