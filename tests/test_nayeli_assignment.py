from pathlib import Path

from repositories.asignacion_repository import (
    AsignacionRepository,
)
from repositories.estado_repository import (
    EstadoRepository,
)


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
assignment_repository = AsignacionRepository()

estado_id = estado_repository.get_id_by_pdf(
    latest_pdf
)

assignment_repository.prepare_person_relation()

first_assignment = (
    assignment_repository.assign_nayeli_automatically(
        estado_id
    )
)

second_assignment = (
    assignment_repository.assign_nayeli_automatically(
        estado_id
    )
)

total_assigned = (
    assignment_repository.count_nayeli_assignments(
        estado_id
    )
)

print("=" * 60)
print("ASIGNACIÓN AUTOMÁTICA DE NAYELI")
print("=" * 60)
print("Primera asignación:", first_assignment)
print("Segunda asignación:", second_assignment)
print("Total asignado a Nayeli:", total_assigned)