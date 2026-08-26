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

print("=" * 60)
print("CONSUMOS PENDIENTES DE ANGEL")
print("=" * 60)
print("Total pendiente:", len(pending))
print()

for number, consumption in enumerate(
    pending,
    start=1,
):
    print(
        f"{number}. "
        f"{consumption['fecha']} | "
        f"{consumption['descripcion']} | "
        f"S/ {consumption['soles']:.2f}"
    )