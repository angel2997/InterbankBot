from pathlib import Path

from repositories.consumo_repository import (
    ConsumoRepository,
)
from repositories.estado_repository import (
    EstadoRepository,
)
from services.pdf_service import PdfService


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_FOLDER = PROJECT_DIR / "pdf"

pdf_files = list(PDF_FOLDER.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(
        "No existen archivos PDF descargados"
    )

latest_pdf = max(
    pdf_files,
    key=lambda file: file.stat().st_mtime,
)

estado_repository = EstadoRepository()
consumo_repository = ConsumoRepository()

estado_repository.create_table()
consumo_repository.create_table()

if not estado_repository.is_processed(latest_pdf):
    estado_repository.register(
        pdf_path=latest_pdf,
        status="EXTRAIDO",
    )

estado_id = estado_repository.get_id_by_pdf(
    latest_pdf
)

pdf_service = PdfService()

result = pdf_service.extract_consumptions(
    latest_pdf
)

all_consumptions = (
    result["angel"]
    + result["nayeli"]
    + result["insurance"]
)

first_insert = consumo_repository.save_many(
    estado_id,
    all_consumptions,
)

second_insert = consumo_repository.save_many(
    estado_id,
    all_consumptions,
)

total_saved = (
    consumo_repository.count_by_statement(
        estado_id
    )
)

print("=" * 60)
print("CONSUMOS GUARDADOS")
print("=" * 60)
print("Primera inserción:", first_insert)
print("Segunda inserción:", second_insert)
print("Total almacenado:", total_saved)