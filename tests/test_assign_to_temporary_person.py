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
asignacion_repository = AsignacionRepository()

estado_id = estado_repository.get_id_by_pdf(
    latest_pdf
)

pending = (
    asignacion_repository
    .list_pending_angel_consumptions(
        estado_id
    )
)

if not pending:
    raise LookupError(
        "No existen consumos pendientes"
    )

consumption = pending[0]

assigned = asignacion_repository.assign_consumption(
    consumption_id=consumption["id"],
    person_name="Flor",
)

result = asignacion_repository.get_consumption_assignment(
    consumption["id"]
)

remaining = (
    asignacion_repository
    .list_pending_angel_consumptions(
        estado_id
    )
)

print("=" * 60)
print("ASIGNACIÓN A PERSONA TEMPORAL")
print("=" * 60)
print("Asignado:", assigned)
print("Descripción:", result["descripcion"])
print("Persona:", result["persona"])
print("Tipo:", result["asignacion"])
print("Pendientes restantes:", len(remaining))