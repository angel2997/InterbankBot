import re
from decimal import Decimal
from decimal import ROUND_HALF_UP

from repositories.asignacion_repository import (
    AsignacionRepository,
)
from repositories.movimiento_asignacion_repository import (
    MovimientoAsignacionRepository,
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
        self.movimiento_repository = (
            MovimientoAsignacionRepository()
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


    def process_person_selection(
        self,
        estado_id,
        consumption_id,
        selected_option,
        options,
    ):
        option = str(
            selected_option
        ).strip()

        if option not in options:
            return {
                "valid": False,
                "action": "invalid_option",
                "message": (
                    "La opción ingresada no es válida. "
                    "Selecciona uno de los números "
                    "mostrados en la lista."
                ),
                "person_id": None,
                "person_name": None,
            }

        selected_value = options[option]

        if selected_value == "__NEW_PERSON__":
            return {
                "valid": True,
                "action": "request_new_person_name",
                "message": (
                    "Escribe el nombre de la "
                    "nueva persona."
                ),
                "estado_id": estado_id,
                "consumption_id": consumption_id,
                "person_id": None,
                "person_name": None,
            }

        person = (
            self.persona_repository
            .find_by_name(
                selected_value
            )
        )

        if person is None:
            raise LookupError(
                "La persona seleccionada "
                "ya no existe"
            )

        balance = (
            self.movimiento_repository
            .get_balance(
                consumption_id
            )
        )

        if balance["completed"]:
            raise ValueError(
                "El consumo ya fue asignado "
                "completamente"
            )

        currency_symbol = (
            "S/"
            if balance["currency"] == "PEN"
            else "US$"
        )

        amount_question = (
            self.build_assignment_amount_question(
                person_name=person["nombre"],
                pending_cents=(
                    balance["pending_cents"]
                ),
                currency_symbol=currency_symbol,
            )
        )

        return {
            "valid": True,
            "action": "request_amount",
            "message": amount_question,
            "estado_id": estado_id,
            "consumption_id": consumption_id,
            "person_id": person["id"],
            "person_name": person["nombre"],
            "pending_cents": (
                balance["pending_cents"]
            ),
            "currency": balance["currency"],
            "currency_symbol": currency_symbol,
        }

    def create_temporary_person(
        self,
        estado_id,
        consumption_id,
        person_name,
    ):
        normalized_name = " ".join(
            str(person_name).split()
        )

        if not normalized_name:
            return {
                "created": False,
                "action": "request_new_person_name",
                "message": (
                    "El nombre de la persona "
                    "no puede estar vacío. "
                    "Escribe un nombre válido."
                ),
                "person_id": None,
                "person_name": None,
            }

        existing_person = (
            self.persona_repository
            .find_by_name(
                normalized_name
            )
        )

        if existing_person is not None:
            return {
                "created": False,
                "action": "person_already_exists",
                "message": (
                    f'La persona "'
                    f'{existing_person["nombre"]}'
                    f'" ya existe.\n\n'
                    "Selecciónala de la lista "
                    "o escribe otro nombre."
                ),
                "person_id": (
                    existing_person["id"]
                ),
                "person_name": (
                    existing_person["nombre"]
                ),
            }

        created = (
            self.persona_repository
            .add_temporary_person(
                estado_id=estado_id,
                person_name=normalized_name,
            )
        )

        if not created:
            raise RuntimeError(
                "No se pudo crear la "
                "persona temporal"
            )

        person = (
            self.persona_repository
            .find_by_name(
                normalized_name
            )
        )

        if person is None:
            raise RuntimeError(
                "La persona temporal fue creada, "
                "pero no pudo recuperarse"
            )

        balance = (
            self.movimiento_repository
            .get_balance(
                consumption_id
            )
        )

        if balance["completed"]:
            raise ValueError(
                "El consumo ya fue asignado "
                "completamente"
            )

        currency_symbol = (
            "S/"
            if balance["currency"] == "PEN"
            else "US$"
        )

        amount_question = (
            self.build_assignment_amount_question(
                person_name=person["nombre"],
                pending_cents=(
                    balance["pending_cents"]
                ),
                currency_symbol=currency_symbol,
            )
        )

        message = (
            f'{person["nombre"]} fue agregado '
            "como persona temporal.\n\n"
            f"{amount_question}"
        )

        return {
            "created": True,
            "action": "request_amount",
            "message": message,
            "estado_id": estado_id,
            "consumption_id": consumption_id,
            "person_id": person["id"],
            "person_name": person["nombre"],
            "pending_cents": (
                balance["pending_cents"]
            ),
            "currency": balance["currency"],
            "currency_symbol": currency_symbol,
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


    def register_assignment(
        self,
        consumption_id,
        person_id,
        user_input,
    ):
        balance_before = (
            self.movimiento_repository
            .get_balance(
                consumption_id
            )
        )

        if balance_before["completed"]:
            raise ValueError(
                "El consumo ya fue asignado "
                "completamente"
            )

        calculated = (
            self.calculate_assignment_amount(
                user_input=user_input,
                pending_cents=(
                    balance_before[
                        "pending_cents"
                    ]
                ),
            )
        )

        movement_id = (
            self.movimiento_repository
            .add_movement(
                consumption_id=consumption_id,
                person_id=person_id,
                amount_cents=(
                    calculated[
                        "amount_cents"
                    ]
                ),
            )
        )

        movements = (
            self.movimiento_repository
            .list_movements(
                consumption_id
            )
        )

        movement = next(
            item
            for item in movements
            if item["id"] == movement_id
        )

        balance_after = (
            self.movimiento_repository
            .get_balance(
                consumption_id
            )
        )

        currency_symbol = (
            "S/"
            if balance_after["currency"]
            == "PEN"
            else "US$"
        )

        assigned_amount = (
            Decimal(
                calculated["amount_cents"]
            )
            / Decimal("100")
        )

        pending_amount = (
            Decimal(
                balance_after[
                    "pending_cents"
                ]
            )
            / Decimal("100")
        )

        message_lines = [
            "Asignación registrada.",
            "",
            (
                "Persona: "
                f"{movement['persona']}"
            ),
        ]

        if (
            calculated["input_type"]
            == "percentage"
        ):
            message_lines.append(
                (
                    "Porcentaje ingresado: "
                    f"{calculated['input_value']}%"
                )
            )

        message_lines.extend(
            [
                (
                    "Monto asignado: "
                    f"{currency_symbol} "
                    f"{assigned_amount:.2f}"
                ),
                (
                    "Saldo pendiente: "
                    f"{currency_symbol} "
                    f"{pending_amount:.2f}"
                ),
            ]
        )

        if balance_after["completed"]:
            message_lines.extend(
                [
                    "",
                    (
                        "El consumo fue asignado "
                        "completamente."
                    ),
                ]
            )

        return {
            "movement_id": movement_id,
            "person_id": person_id,
            "person_name": (
                movement["persona"]
            ),
            "currency": (
                balance_after["currency"]
            ),
            "currency_symbol": (
                currency_symbol
            ),
            "input_type": (
                calculated["input_type"]
            ),
            "input_value": (
                calculated["input_value"]
            ),
            "assigned_cents": (
                calculated["amount_cents"]
            ),
            "pending_cents": (
                balance_after[
                    "pending_cents"
                ]
            ),
            "completed": (
                balance_after["completed"]
            ),
            "message": "\n".join(
                message_lines
            ),
        }
    
    
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