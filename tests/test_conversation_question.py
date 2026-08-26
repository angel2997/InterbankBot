from pathlib import Path

from repositories.estado_repository import (
    EstadoRepository,
)
from services.conversation_service import (
    ConversationService,
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
conversation_service = ConversationService()

estado_id = estado_repository.get_id_by_pdf(
    latest_pdf
)

result = conversation_service.build_next_question(
    estado_id
)

print("=" * 60)
print("PREGUNTA PARA WHATSAPP")
print("=" * 60)
print(result["message"])
print()
print("Opciones internas:")
print(result["options"])