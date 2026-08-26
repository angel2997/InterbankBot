from decimal import Decimal
from pathlib import Path

from services.pdf_service import PdfService


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_FOLDER = PROJECT_DIR / "pdf"

pdf_files = list(PDF_FOLDER.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(
        "No hay archivos PDF descargados"
    )

latest_pdf = max(
    pdf_files,
    key=lambda file: file.stat().st_mtime,
)

pdf_service = PdfService()

result = pdf_service.extract_consumptions(
    latest_pdf
)

angel = result["angel"]
nayeli = result["nayeli"]
insurance = result["insurance"]

total_angel = sum(
    (item["soles"] for item in angel),
    Decimal("0.00"),
)

total_nayeli = sum(
    (item["soles"] for item in nayeli),
    Decimal("0.00"),
)

total_insurance = sum(
    (item["soles"] for item in insurance),
    Decimal("0.00"),
)

total_general = (
    total_angel
    + total_nayeli
    + total_insurance
)

print("=" * 60)
print("CONSUMOS EXTRAÍDOS")
print("=" * 60)

print("Consumos de Angel:", len(angel))
print("Total Angel:", total_angel)

print("Consumos de Nayeli:", len(nayeli))
print("Total Nayeli:", total_nayeli)

print("Cargos de seguro:", len(insurance))
print("Total seguro:", total_insurance)

print()
print("TOTAL GENERAL:", total_general)

print()
