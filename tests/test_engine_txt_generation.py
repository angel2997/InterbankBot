import unittest
from unittest.mock import MagicMock

from repositories.conversation_session_repository import (
    WAITING_AMOUNT,
)
from services.conversation_engine_service import (
    ConversationEngineService,
)


class EngineTxtGenerationTest(
    unittest.TestCase
):

    def setUp(self):
        self.number = "+51999999999"

        self.conversation_service = (
            MagicMock()
        )

        self.session_repository = (
            MagicMock()
        )

        self.txt_service = MagicMock()

        self.engine = (
            ConversationEngineService(
                conversation_service=(
                    self.conversation_service
                ),
                session_repository=(
                    self.session_repository
                ),
                txt_service=self.txt_service,
            )
        )

        self.session = {
            "numero_whatsapp": self.number,
            "estado_id": 1,
            "consumo_id": 10,
            "estado_conversacion": (
                WAITING_AMOUNT
            ),
            "persona_id": 3,
            "persona_nombre": "Angel",
            "opciones": {},
        }

        (
            self.session_repository
            .get_session
            .return_value
        ) = self.session

        (
            self.conversation_service
            .register_assignment
            .return_value
        ) = {
            "movement_id": 25,
            "person_id": 3,
            "person_name": "Angel",
            "currency": "PEN",
            "currency_symbol": "S/",
            "input_type": "balance",
            "input_value": "Todo",
            "assigned_cents": 5000,
            "pending_cents": 0,
            "completed": True,
            "message": (
                "Asignación registrada.\n\n"
                "Persona: Angel\n"
                "Monto asignado: S/ 50.00\n"
                "Saldo pendiente: S/ 0.00\n\n"
                "El consumo fue asignado "
                "completamente."
            ),
        }

    def test_generates_txt_when_completed(
        self,
    ):
        (
            self.conversation_service
            .build_next_question
            .return_value
        ) = {
            "completed": True,
            "message": (
                "Todos los consumos "
                "fueron asignados."
            ),
            "consumption": None,
            "options": {},
        }

        (
            self.txt_service
            .generate_all_files
            .return_value
        ) = {
            "estado_id": 1,
            "person_files": [],
            "total_file": {
                "file_name": "Total.txt",
                "balanced": True,
            },
            "person_file_count": 3,
            "total_file_count": 1,
            "generated_file_count": 4,
            "generated_paths": [],
            "balanced": True,
        }

        result = self.engine.process_message(
            whatsapp_number=self.number,
            message="Todo",
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertEqual(
            "completed",
            result["action"],
        )

        (
            self.txt_service
            .generate_all_files
            .assert_called_once_with(
                estado_id=1
            )
        )

        (
            self.session_repository
            .delete_session
            .assert_called_once_with(
                self.number
            )
        )

        self.assertEqual(
            4,
            result["txt_result"][
                "generated_file_count"
            ],
        )

        self.assertIn(
            (
                "Archivos TXT generados "
                "correctamente."
            ),
            result["message"],
        )

        self.assertIn(
            (
                "Archivo consolidado: "
                "Total.txt"
            ),
            result["message"],
        )

    def test_does_not_generate_txt_after_partial_amount(
        self,
    ):
        (
            self.conversation_service
            .register_assignment
            .return_value
        ) = {
            "movement_id": 25,
            "assigned_cents": 2500,
            "pending_cents": 2500,
            "completed": False,
            "message": (
                "Asignación registrada."
            ),
        }

        (
            self.conversation_service
            .build_next_question
            .return_value
        ) = {
            "completed": False,
            "message": (
                "Saldo pendiente: S/ 25.00"
            ),
            "consumption": {
                "id": 10,
            },
            "options": {
                "1": "Angel",
                "2": "__NEW_PERSON__",
            },
        }

        (
            self.session_repository
            .update_conversation_state
            .return_value
        ) = {
            "estado_id": 1,
            "consumo_id": 10,
            "estado_conversacion": (
                "ESPERANDO_PERSONA"
            ),
        }

        result = self.engine.process_message(
            whatsapp_number=self.number,
            message="25",
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertEqual(
            "waiting_person",
            result["action"],
        )

        (
            self.txt_service
            .generate_all_files
            .assert_not_called()
        )

        (
            self.session_repository
            .delete_session
            .assert_not_called()
        )

    def test_keeps_session_when_txt_generation_fails(
        self,
    ):
        (
            self.conversation_service
            .build_next_question
            .return_value
        ) = {
            "completed": True,
            "message": (
                "Todos los consumos "
                "fueron asignados."
            ),
            "consumption": None,
            "options": {},
        }

        (
            self.txt_service
            .generate_all_files
            .side_effect
        ) = OSError(
            "No se pudo escribir en la carpeta txt"
        )

        result = self.engine.process_message(
            whatsapp_number=self.number,
            message="Todo",
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertEqual(
            "txt_generation_failed",
            result["action"],
        )

        self.assertIsNotNone(
            result["session"]
        )

        (
            self.session_repository
            .delete_session
            .assert_not_called()
        )

        self.assertIn(
            (
                "no se pudieron generar "
                "los archivos TXT"
            ),
            result["message"],
        )

        self.assertIn(
            (
                "La sesión se conservará"
            ),
            result["message"],
        )

    def test_warns_when_total_is_not_balanced(
        self,
    ):
        (
            self.conversation_service
            .build_next_question
            .return_value
        ) = {
            "completed": True,
            "message": (
                "Todos los consumos "
                "fueron asignados."
            ),
            "consumption": None,
            "options": {},
        }

        (
            self.txt_service
            .generate_all_files
            .return_value
        ) = {
            "estado_id": 1,
            "person_files": [],
            "total_file": {
                "file_name": "Total.txt",
                "balanced": False,
            },
            "person_file_count": 3,
            "total_file_count": 1,
            "generated_file_count": 4,
            "generated_paths": [],
            "balanced": False,
        }

        result = self.engine.process_message(
            whatsapp_number=self.number,
            message="Todo",
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertFalse(
            result["txt_result"][
                "balanced"
            ]
        )

        self.assertIn(
            (
                "Total.txt presenta una "
                "diferencia pendiente"
            ),
            result["message"],
        )

        (
            self.session_repository
            .delete_session
            .assert_called_once_with(
                self.number
            )
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )