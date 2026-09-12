import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.whatsapp_service import (
    WhatsappService,
)
from unittest.mock import MagicMock

from services.conversation_engine_service import (
    ConversationEngineService,
)


class WhatsappServiceTest(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.original_db_path = (
            database_module.DB_PATH
        )

        database_module.DB_PATH = (
            Path(
                self.temporary_directory.name
            )
            / "test.db"
        )

        self._create_base_tables()
        self._insert_test_data()

        self.allowed_number = (
            "+51999999999"
        )

        self.txt_service = MagicMock()

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
            "person_file_count": 1,
            "total_file_count": 1,
            "generated_file_count": 2,
            "generated_paths": [],
            "balanced": True,
        }

        conversation_engine = (
            ConversationEngineService(
                txt_service=self.txt_service
            )
        )

        self.service = WhatsappService(
            allowed_number=(
                self.allowed_number
            ),
            conversation_engine=(
                conversation_engine
            ),
        )

        self.service.prepare_tables()

    def tearDown(self):
        database_module.DB_PATH = (
            self.original_db_path
        )

        self.temporary_directory.cleanup()

    def _create_base_tables(self):
        with get_connection() as connection:
            connection.executescript(
                """
                CREATE TABLE estados_procesados (
                    id INTEGER
                        PRIMARY KEY AUTOINCREMENT,
                    periodo TEXT NOT NULL
                );

                CREATE TABLE personas (
                    id INTEGER
                        PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL
                        COLLATE NOCASE UNIQUE,
                    permanente INTEGER NOT NULL
                        CHECK (
                            permanente IN (0, 1)
                        )
                );

                CREATE TABLE estado_personas (
                    estado_id INTEGER NOT NULL,
                    persona_id INTEGER NOT NULL,
                    PRIMARY KEY (
                        estado_id,
                        persona_id
                    ),
                    FOREIGN KEY (estado_id)
                        REFERENCES
                            estados_procesados(id),
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                );

                CREATE TABLE consumos (
                    id INTEGER
                        PRIMARY KEY AUTOINCREMENT,
                    estado_id INTEGER NOT NULL,
                    fecha TEXT NOT NULL,
                    descripcion TEXT NOT NULL,
                    monto_soles_centimos
                        INTEGER NOT NULL,
                    monto_dolares_centimos
                        INTEGER NOT NULL,
                    titular TEXT NOT NULL,
                    asignacion TEXT NOT NULL,
                    persona_asignada TEXT,
                    persona_id INTEGER,
                    FOREIGN KEY (estado_id)
                        REFERENCES
                            estados_procesados(id),
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                );
                """
            )

    def _insert_test_data(self):
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO estados_procesados (
                    periodo
                )
                VALUES (?)
                """,
                ("2026-08",),
            )

            connection.executemany(
                """
                INSERT INTO personas (
                    nombre,
                    permanente
                )
                VALUES (?, ?)
                """,
                (
                    ("Angel", 1),
                    ("Flor", 0),
                ),
            )

            connection.execute(
                """
                INSERT INTO estado_personas (
                    estado_id,
                    persona_id
                )
                VALUES (?, ?)
                """,
                (1, 2),
            )

            connection.execute(
                """
                INSERT INTO consumos (
                    estado_id,
                    fecha,
                    descripcion,
                    monto_soles_centimos,
                    monto_dolares_centimos,
                    titular,
                    asignacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    "01-Ago",
                    "Consumo de prueba",
                    10000,
                    0,
                    "Angel",
                    "PENDIENTE",
                ),
            )

    def test_starts_authorized_conversation(
        self,
    ):
        result = (
            self.service
            .start_conversation(
                whatsapp_number=(
                    self.allowed_number
                ),
                estado_id=1,
            )
        )

        self.assertEqual(
            "waiting_person",
            result["action"],
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

    def test_normalizes_number_spaces(
        self,
    ):
        result = (
            self.service
            .start_conversation(
                whatsapp_number=(
                    "+51 999 999 999"
                ),
                estado_id=1,
            )
        )

        self.assertEqual(
            "waiting_person",
            result["action"],
        )

        session = (
            self.service
            .get_active_session(
                self.allowed_number
            )
        )

        self.assertIsNotNone(
            session
        )

    def test_rejects_unauthorized_number(
        self,
    ):
        with self.assertRaisesRegex(
            PermissionError,
            "no está autorizado",
        ):
            self.service.start_conversation(
                whatsapp_number=(
                    "+51888888888"
                ),
                estado_id=1,
            )

    def test_processes_person_selection(
        self,
    ):
        self.service.start_conversation(
            self.allowed_number,
            1,
        )

        result = (
            self.service.receive_message(
                whatsapp_number=(
                    self.allowed_number
                ),
                message="1",
            )
        )

        self.assertTrue(
            result["accepted"]
        )

        self.assertEqual(
            "waiting_amount",
            result["action"],
        )

        self.assertIn(
            "¿Cuánto deseas asignar",
            result["message"],
        )

    def test_processes_partial_amount(
        self,
    ):
        self.service.start_conversation(
            self.allowed_number,
            1,
        )

        self.service.receive_message(
            self.allowed_number,
            "1",
        )

        result = (
            self.service.receive_message(
                self.allowed_number,
                "50%",
            )
        )

        self.assertTrue(
            result["accepted"]
        )

        self.assertEqual(
            "waiting_person",
            result["action"],
        )

        self.assertEqual(
            5000,
            result["assignment"][
                "assigned_cents"
            ],
        )

        self.assertIn(
            "Saldo pendiente: S/ 50.00",
            result["message"],
        )

    def test_completes_conversation(
        self,
    ):
        self.service.start_conversation(
            self.allowed_number,
            1,
        )

        self.service.receive_message(
            self.allowed_number,
            "1",
        )

        result = (
            self.service.receive_message(
                self.allowed_number,
                "Todo",
            )
        )

        self.assertTrue(
            result["accepted"]
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertEqual(
            "completed",
            result["action"],
        )

        self.assertIsNone(
            self.service.get_active_session(
                self.allowed_number
            )
        )

    def test_rejects_empty_message(
        self,
    ):
        self.service.start_conversation(
            self.allowed_number,
            1,
        )

        result = (
            self.service.receive_message(
                self.allowed_number,
                "   ",
            )
        )

        self.assertFalse(
            result["accepted"]
        )

        self.assertEqual(
            "empty_message",
            result["action"],
        )

    def test_reports_missing_conversation(
        self,
    ):
        result = (
            self.service.receive_message(
                self.allowed_number,
                "1",
            )
        )

        self.assertFalse(
            result["accepted"]
        )

        self.assertEqual(
            "no_active_conversation",
            result["action"],
        )

    def test_cancels_active_conversation(
        self,
    ):
        self.service.start_conversation(
            self.allowed_number,
            1,
        )

        result = (
            self.service
            .cancel_conversation(
                self.allowed_number
            )
        )

        self.assertTrue(
            result["cancelled"]
        )

        self.assertEqual(
            "conversation_cancelled",
            result["action"],
        )

        self.assertIsNone(
            self.service.get_active_session(
                self.allowed_number
            )
        )

    def test_reports_no_session_to_cancel(
        self,
    ):
        result = (
            self.service
            .cancel_conversation(
                self.allowed_number
            )
        )

        self.assertFalse(
            result["cancelled"]
        )

        self.assertEqual(
            "no_active_conversation",
            result["action"],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )