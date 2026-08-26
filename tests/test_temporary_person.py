from pathlib import Path

from repositories.estado_repository import (
    EstadoRepository,
)
from repositories.persona_repository import (
    PersonaRepository,
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
persona_repository = PersonaRepository()

estado_id = estado_repository.get_id_by_pdf(
    latest_pdf
)

persona_repository.create_table()
persona_repository.create_statement_people_table()

first_insert = persona_repository.add_temporary_person(
    estado_id=estado_id,
    person_name="Flor",
)

second_insert = persona_repository.add_temporary_person(
    estado_id=estado_id,
    person_name="Flor",
)

people = persona_repository.list_people_for_statement(
    estado_id
)

print("=" * 60)
print("PERSONAS DEL ESTADO DE CUENTA")
print("=" * 60)
print("Primera creación de Flor:", first_insert)
print("Segunda creación de Flor:", second_insert)
print("Total disponible:", len(people))
print()

for person in people:
    person_type = (
        "Permanente"
        if person["permanente"]
        else "Temporal"
    )

    print(
        person["nombre"],
        "-",
        person_type,
    )