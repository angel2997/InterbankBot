import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from main import run_console


class ConsoleSimulatorTest(
    unittest.TestCase
):

    def setUp(self):
        self.number = "+51999999999"

        self.service = MagicMock()

        self.service.get_active_session.return_value = (
            None
        )

        self.service.start_conversation.return_value = {
            "action": "waiting_person",
            "completed": False,
            "message": (
                "Selecciona una persona."
            ),
        }

        self.outputs = []

    def output_function(
        self,
        message="",
    ):
        self.outputs.append(
            str(message)
        )

    def test_prepares_tables(
        self,
    ):
        messages = iter(
            [
                "Salir",
            ]
        )

        run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

        (
            self.service
            .prepare_tables
            .assert_called_once_with()
        )

    def test_starts_new_conversation(
        self,
    ):
        messages = iter(
            [
                "Salir",
            ]
        )

        run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

        (
            self.service
            .start_conversation
            .assert_called_once_with(
                whatsapp_number=self.number,
                estado_id=1,
            )
        )

        self.assertIn(
            "Selecciona una persona.",
            self.outputs,
        )

    def test_processes_messages_until_complete(
        self,
    ):
        messages = iter(
            [
                "1",
                "Todo",
            ]
        )

        self.service.receive_message.side_effect = [
            {
                "accepted": True,
                "action": "waiting_amount",
                "completed": False,
                "message": (
                    "Ingresa el monto."
                ),
            },
            {
                "accepted": True,
                "action": "completed",
                "completed": True,
                "message": (
                    "Todos los consumos "
                    "fueron asignados."
                ),
            },
        ]

        result = run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertEqual(
            "completed",
            result["action"],
        )

        self.assertEqual(
            2,
            (
                self.service
                .receive_message
                .call_count
            ),
        )

        self.assertIn(
            "Ingresa el monto.",
            self.outputs,
        )

        self.assertIn(
            (
                "Todos los consumos "
                "fueron asignados."
            ),
            self.outputs,
        )

    def test_exit_preserves_session(
        self,
    ):
        messages = iter(
            [
                "Salir",
            ]
        )

        result = run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

        self.assertEqual(
            "simulator_closed",
            result["action"],
        )

        (
            self.service
            .cancel_conversation
            .assert_not_called()
        )

        (
            self.service
            .receive_message
            .assert_not_called()
        )

    def test_cancel_deletes_session(
        self,
    ):
        messages = iter(
            [
                "Cancelar",
            ]
        )

        self.service.cancel_conversation.return_value = {
            "cancelled": True,
            "action": (
                "conversation_cancelled"
            ),
            "message": (
                "La conversación fue cancelada."
            ),
        }

        result = run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

        self.assertTrue(
            result["cancelled"]
        )

        self.assertEqual(
            "conversation_cancelled",
            result["action"],
        )

        (
            self.service
            .cancel_conversation
            .assert_called_once_with(
                self.number
            )
        )

    def test_recovers_existing_session(
        self,
    ):
        self.service.get_active_session.return_value = {
            "numero_whatsapp": self.number,
            "estado_id": 1,
            "consumo_id": 1,
            "estado_conversacion": (
                "ESPERANDO_PERSONA"
            ),
            "persona_id": None,
            "persona_nombre": None,
            "opciones": {
                "1": "Angel",
            },
        }

        conversation_service = (
            self.service
            .conversation_engine
            .conversation_service
        )

        (
            conversation_service
            .build_next_question
            .return_value
        ) = {
            "completed": False,
            "message": (
                "Conversación recuperada."
            ),
            "consumption": {
                "id": 1,
            },
            "options": {
                "1": "Angel",
            },
        }

        messages = iter(
            [
                "Salir",
            ]
        )

        run_console(
            estado_id=1,
            whatsapp_number=self.number,
            whatsapp_service=self.service,
            input_function=lambda _: next(
                messages
            ),
            output_function=(
                self.output_function
            ),
        )

if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )

        