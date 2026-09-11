import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.conversation_service import (
    ConversationService,
)


class ConversationUndoTest(
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

        self.service = ConversationService()

        (
            self.service
            .movimiento_repository
            .create_table()
        )

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
                    monto_soles_centimos
                        INTEGER NOT NULL,
                    monto_dolares_centimos
                        INTEGER NOT NULL,
                    FOREIGN KEY (estado_id)
                        REFERENCES
                            estados_procesados(id)
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
                    ("Flor", 0),
                    ("Angel", 1),
                    ("Fernando", 1),
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
                (1, 1),
            )

            connection.executemany(
                """
                INSERT INTO consumos (
                    estado_id,
                    monto_soles_centimos,
                    monto_dolares_centimos
                )
                VALUES (?, ?, ?)
                """,
                (
                    (1, 10000, 0),
                    (1, 0, 8000),
                ),
            )

    def test_deletes_only_last_assignment(
        self,
    ):
        first = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="20",
            )
        )

        second = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=2,
                user_input="30",
            )
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=1
            )
        )

        movements = (
            self.service
            .movimiento_repository
            .list_movements(1)
        )

        self.assertTrue(
            result["deleted"]
        )

        self.assertEqual(
            "assignment_undone",
            result["action"],
        )

        self.assertEqual(
            second["movement_id"],
            result["movement_id"],
        )

        self.assertEqual(
            "Angel",
            result["person_name"],
        )

        self.assertEqual(
            3000,
            result["deleted_cents"],
        )

        self.assertEqual(
            8000,
            result["pending_cents"],
        )

        self.assertEqual(
            1,
            len(movements),
        )

        self.assertEqual(
            first["movement_id"],
            movements[0]["id"],
        )

    def test_restores_balance_after_undo(
        self,
    ):
        self.service.register_assignment(
            consumption_id=1,
            person_id=1,
            user_input="25",
        )

        self.service.register_assignment(
            consumption_id=1,
            person_id=3,
            user_input="50%",
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=1
            )
        )

        self.assertEqual(
            7500,
            result["pending_cents"],
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertIn(
            "Saldo pendiente: S/ 75.00",
            result["message"],
        )

    def test_can_undo_completed_consumption(
        self,
    ):
        assignment = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=2,
                user_input="Todo",
            )
        )

        self.assertTrue(
            assignment["completed"]
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=1
            )
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertEqual(
            10000,
            result["pending_cents"],
        )

        self.assertEqual(
            10000,
            result["deleted_cents"],
        )

    def test_message_identifies_deleted_assignment(
        self,
    ):
        self.service.register_assignment(
            consumption_id=1,
            person_id=1,
            user_input="35.50",
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=1
            )
        )

        self.assertIn(
            "Última asignación eliminada.",
            result["message"],
        )

        self.assertIn(
            "Persona: Flor",
            result["message"],
        )

        self.assertIn(
            "Monto eliminado: S/ 35.50",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

    def test_preserves_dollar_currency(
        self,
    ):
        self.service.register_assignment(
            consumption_id=2,
            person_id=3,
            user_input="50%",
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=2
            )
        )

        self.assertEqual(
            "USD",
            result["currency"],
        )

        self.assertEqual(
            "US$",
            result["currency_symbol"],
        )

        self.assertEqual(
            4000,
            result["deleted_cents"],
        )

        self.assertEqual(
            8000,
            result["pending_cents"],
        )

        self.assertIn(
            "Monto eliminado: US$ 40.00",
            result["message"],
        )

    def test_rejects_undo_without_assignments(
        self,
    ):
        with self.assertRaisesRegex(
            LookupError,
            "no tiene asignaciones",
        ):
            self.service.undo_last_assignment(
                consumption_id=1
            )

    def test_can_undo_repeated_person_movement(
        self,
    ):
        first = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="20",
            )
        )

        second = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="10",
            )
        )

        result = (
            self.service.undo_last_assignment(
                consumption_id=1
            )
        )

        movements = (
            self.service
            .movimiento_repository
            .list_movements(1)
        )

        self.assertEqual(
            second["movement_id"],
            result["movement_id"],
        )

        self.assertEqual(
            1000,
            result["deleted_cents"],
        )

        self.assertEqual(
            1,
            len(movements),
        )

        self.assertEqual(
            first["movement_id"],
            movements[0]["id"],
        )

        self.assertEqual(
            8000,
            result["pending_cents"],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )