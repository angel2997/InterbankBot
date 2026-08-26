from pathlib import Path

from repositories.estado_repository import (
    EstadoRepository,
)


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

repository = EstadoRepository()
repository.create_table()

print(
    "Procesado antes:",
    repository.is_processed(latest_pdf),
)

first_registration = repository.register(
    pdf_path=latest_pdf,
    email_date="2026-08-01T23:52:43Z",
    period="2026-07",
)

print(
    "Primer registro creado:",
    first_registration,
)

second_registration = repository.register(
    pdf_path=latest_pdf,
    email_date="2026-08-01T23:52:43Z",
    period="2026-07",
)

print(
    "Segundo registro creado:",
    second_registration,
)

print(
    "Procesado después:",
    repository.is_processed(latest_pdf),
)