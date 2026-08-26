from repositories.asignacion_repository import (
    AsignacionRepository,
)
from repositories.persona_repository import (
    PersonaRepository,
)


class ConversationService:

    def __init__(self):
        self.asignacion_repository = (
            AsignacionRepository()
        )
        self.persona_repository = (
            PersonaRepository()
        )

    def build_next_question(self, estado_id):
        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id
            )
        )

        if not pending:
            return {
                "completed": True,
                "message": (
                    "Todos los consumos fueron asignados."
                ),
                "consumption": None,
                "options": {},
            }

        consumption = pending[0]

        people = (
            self.persona_repository
            .list_people_for_statement(
                estado_id
            )
        )

        options = {}

        message_lines = [
            f"Consumo pendiente 1 de {len(pending)}",
            "",
            f"Fecha: {consumption['fecha']}",
            (
                "Descripción: "
                f"{consumption['descripcion']}"
            ),
            f"Monto: S/ {consumption['soles']:.2f}",
            "",
            "¿A quién pertenece?",
        ]

        for number, person in enumerate(
            people,
            start=1,
        ):
            options[str(number)] = person["nombre"]

            person_type = (
                ""
                if person["permanente"]
                else " (temporal)"
            )

            message_lines.append(
                f"{number}. "
                f"{person['nombre']}"
                f"{person_type}"
            )

        new_person_option = str(len(options) + 1)

        options[new_person_option] = (
            "__NEW_PERSON__"
        )

        message_lines.append(
            f"{new_person_option}. Nueva persona"
        )

        return {
            "completed": False,
            "message": "\n".join(message_lines),
            "consumption": consumption,
            "options": options,
        }