import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.conversation_session_repository import (
    WAITING_AMOUNT,
)
from repositories.conversation_session_repository import (
    WAITING_NEW_PERSON_NAME,
)
from repositories.conversation_session_repository import (
    WAITING_PERSON,
)
from services.conversation_engine_service import (
    ConversationEngineService,
)


class ConversationEngineTest(
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

        self.engine = (
            ConversationEngineService()
        )

        (
            self.engine
            .conversation_service
            .movimiento_repository
            .create_table()
        )

        (
            self.engine
            .session_repository
            .create_table()
        )

        self.number = "+51999999999"

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

    def test_starts_conversation(
        self,
    ):
        result = (
            self.engine.start_conversation(
                whatsapp_number=self.number,
                estado_id=1,
            )
        )

        self.assertEqual(
            "waiting_person",
            result["action"],
        )

        self.assertEqual(
            WAITING_PERSON,
            result["session"][
                "estado_conversacion"
            ],
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

    def test_selects_existing_person(
        self,
    ):
        self.engine.start_conversation(
            self.number,
            1,
        )

        result = (
            self.engine.process_message(
                self.number,
                "1",
            )
        )

        self.assertEqual(
            "waiting_amount",
            result["action"],
        )

        self.assertEqual(
            WAITING_AMOUNT,
            result["session"][
                "estado_conversacion"
            ],
        )

        self.assertEqual(
            "Angel",
            result["session"][
                "persona_nombre"
            ],
        )

    def test_requests_new_person_name(
        self,
    ):
        started = (
            self.engine.start_conversation(
                self.number,
                1,
            )
        )

        new_person_option = next(
            option
            for option, value
            in started["session"][
                "opciones"
            ].items()
            if value == "__NEW_PERSON__"
        )

        result = (
            self.engine.process_message(
                self.number,
                new_person_option,
            )
        )

        self.assertEqual(
            "waiting_new_person_name",
            result["action"],
        )

        self.assertEqual(
            WAITING_NEW_PERSON_NAME,
            result["session"][
                "estado_conversacion"
            ],
        )

    def test_creates_person_and_requests_amount(
        self,
    ):
        started = (
            self.engine.start_conversation(
                self.number,
                1,
            )
        )

        new_option = next(
            option
            for option, value
            in started["session"][
                "opciones"
            ].items()
            if value == "__NEW_PERSON__"
        )

        self.engine.process_message(
            self.number,
            new_option,
        )

        result = (
            self.engine.process_message(
                self.number,
                "Carlos",
            )
        )

        self.assertEqual(
            "waiting_amount",
            result["action"],
        )

        self.assertEqual(
            WAITING_AMOUNT,
            result["session"][
                "estado_conversacion"
            ],
        )

        self.assertEqual(
            "Carlos",
            result["session"][
                "persona_nombre"
            ],
        )

    def test_registers_partial_percentage(
        self,
    ):
        self.engine.start_conversation(
            self.number,
            1,
        )

        self.engine.process_message(
            self.number,
            "1",
        )

        result = (
            self.engine.process_message(
                self.number,
                "50%",
            )
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
        self.engine.start_conversation(
            self.number,
            1,
        )

        self.engine.process_message(
            self.number,
            "1",
        )

        result = (
            self.engine.process_message(
                self.number,
                "Todo",
            )
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertEqual(
            "completed",
            result["action"],
        )

        self.assertIsNone(
            self.engine
            .session_repository
            .get_session(
                self.number
            )
        )

    def test_rejects_invalid_amount(
        self,
    ):
        self.engine.start_conversation(
            self.number,
            1,
        )

        self.engine.process_message(
            self.number,
            "1",
        )

        result = (
            self.engine.process_message(
                self.number,
                "200",
            )
        )

        self.assertEqual(
            "invalid_amount",
            result["action"],
        )

        self.assertEqual(
            WAITING_AMOUNT,
            result["session"][
                "estado_conversacion"
            ],
        )

    def test_undoes_last_assignment(
        self,
    ):
        self.engine.start_conversation(
            self.number,
            1,
        )

        self.engine.process_message(
            self.number,
            "1",
        )

        self.engine.process_message(
            self.number,
            "40",
        )

        result = (
            self.engine.process_message(
                self.number,
                "Deshacer",
            )
        )

        self.assertEqual(
            "assignment_undone",
            result["action"],
        )

        self.assertEqual(
            10000,
            result["undo"][
                "pending_cents"
            ],
        )

        self.assertIn(
            "Última asignación eliminada.",
            result["message"],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )