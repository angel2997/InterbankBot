import re
from decimal import Decimal
from decimal import ROUND_HALF_UP

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

        new_person_option = str(
            len(options) + 1
        )

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

    def build_assignment_amount_question(
        self,
        person_name,
        pending_cents,
        currency_symbol,
    ):
        if pending_cents <= 0:
            raise ValueError(
                "El saldo pendiente debe ser "
                "mayor que cero"
            )

        pending_amount = (
            Decimal(pending_cents)
            / Decimal("100")
        )

        message_lines = [
            (
                "¿Cuánto deseas asignar "
                f"a {person_name}?"
            ),
            "",
            (
                "Saldo pendiente: "
                f"{currency_symbol} "
                f"{pending_amount:.2f}"
            ),
            "",
            "Puedes ingresar:",
            (
                "- Un monto: 50, 50.5, 50.50, "
                "S/ 50 o S/50.50"
            ),
            (
                "- Un porcentaje del saldo "
                "pendiente: 50% o 33.33%"
            ),
            (
                "- Todo o Saldo para asignar "
                "el saldo completo"
            ),
        ]

        return "\n".join(message_lines)

    def calculate_assignment_amount(
        self,
        user_input,
        pending_cents,
    ):
        if pending_cents <= 0:
            raise ValueError(
                "El saldo pendiente debe ser "
                "mayor que cero"
            )

        value = str(user_input).strip()

        if not value:
            raise ValueError(
                "Debes ingresar un monto, "
                "porcentaje, Todo o Saldo"
            )

        if value.casefold() in {
            "todo",
            "saldo",
        }:
            return {
                "input_type": "balance",
                "input_value": value,
                "amount_cents": pending_cents,
            }

        if value.endswith("%"):
            return (
                self._calculate_percentage_amount(
                    value=value,
                    pending_cents=pending_cents,
                )
            )

        return self._calculate_fixed_amount(
            value=value,
            pending_cents=pending_cents,
        )

    @staticmethod
    def _calculate_percentage_amount(
        value,
        pending_cents,
    ):
        percentage_text = (
            value[:-1].strip()
        )

        valid_percentage = re.fullmatch(
            r"\d+(?:\.\d{1,2})?",
            percentage_text,
        )

        if valid_percentage is None:
            raise ValueError(
                "El porcentaje debe tener un "
                "formato como 50% o 33.33%"
            )

        percentage = Decimal(
            percentage_text
        )

        if percentage <= 0:
            raise ValueError(
                "El porcentaje debe ser "
                "mayor que cero"
            )

        if percentage > 100:
            raise ValueError(
                "El porcentaje no puede "
                "ser mayor que 100"
            )

        calculated_cents = (
            Decimal(pending_cents)
            * percentage
            / Decimal("100")
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )

        amount_cents = int(
            calculated_cents
        )

        if amount_cents <= 0:
            raise ValueError(
                "El porcentaje ingresado "
                "produce un monto menor "
                "a un centavo"
            )

        if amount_cents > pending_cents:
            raise ValueError(
                "El monto calculado no puede "
                "superar el saldo pendiente"
            )

        return {
            "input_type": "percentage",
            "input_value": percentage,
            "amount_cents": amount_cents,
        }

    @staticmethod
    def _calculate_fixed_amount(
        value,
        pending_cents,
    ):
        amount_text = re.sub(
            r"^S/\s*",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()

        valid_amount = re.fullmatch(
            r"\d+(?:\.\d{1,2})?",
            amount_text,
        )

        if valid_amount is None:
            raise ValueError(
                "El monto debe tener un formato "
                "como 50, 50.5, 50.50, "
                "S/ 50 o S/50.50"
            )

        amount = Decimal(
            amount_text
        )

        amount_cents = int(
            amount * Decimal("100")
        )

        if amount_cents <= 0:
            raise ValueError(
                "El monto debe ser "
                "mayor que cero"
            )

        if amount_cents > pending_cents:
            raise ValueError(
                "El monto no puede superar "
                "el saldo pendiente"
            )

        return {
            "input_type": "amount",
            "input_value": amount,
            "amount_cents": amount_cents,
        }