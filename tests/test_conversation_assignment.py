import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.conversation_service import (
    ConversationService,
)


class ConversationAssignmentTest(
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

    def test_registers_fixed_amount(
        self,
    ):
        result = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="S/ 25.50",
            )
        )

        self.assertEqual(
            "Flor",
            result["person_name"],
        )

        self.assertEqual(
            "PEN",
            result["currency"],
        )

        self.assertEqual(
            2550,
            result["assigned_cents"],
        )

        self.assertEqual(
            7450,
            result["pending_cents"],
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertIn(
            "Monto asignado: S/ 25.50",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 74.50",
            result["message"],
        )

    def test_percentage_uses_current_balance(
        self,
    ):
        self.service.register_assignment(
            consumption_id=1,
            person_id=1,
            user_input="40",
        )

        result = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=2,
                user_input="50%",
            )
        )

        self.assertEqual(
            3000,
            result["assigned_cents"],
        )

        self.assertEqual(
            3000,
            result["pending_cents"],
        )

        self.assertEqual(
            "percentage",
            result["input_type"],
        )

        self.assertIn(
            "Porcentaje ingresado: 50%",
            result["message"],
        )

    def test_saves_repeated_person_as_separate_movements(
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

        movements = (
            self.service
            .movimiento_repository
            .list_movements(1)
        )

        self.assertNotEqual(
            first["movement_id"],
            second["movement_id"],
        )

        self.assertEqual(
            2,
            len(movements),
        )

        amounts = [
            movement["monto_centimos"]
            for movement in movements
        ]

        self.assertEqual(
            [2000, 1000],
            amounts,
        )

    def test_todo_completes_consumption(
        self,
    ):
        self.service.register_assignment(
            consumption_id=1,
            person_id=1,
            user_input="25",
        )

        result = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=2,
                user_input="Todo",
            )
        )

        self.assertEqual(
            7500,
            result["assigned_cents"],
        )

        self.assertEqual(
            0,
            result["pending_cents"],
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertIn(
            (
                "El consumo fue asignado "
                "completamente."
            ),
            result["message"],
        )

    def test_saldo_completes_consumption(
        self,
    ):
        result = (
            self.service.register_assignment(
                consumption_id=1,
                person_id=2,
                user_input="Saldo",
            )
        )

        self.assertEqual(
            10000,
            result["assigned_cents"],
        )

        self.assertTrue(
            result["completed"]
        )

    def test_preserves_dollar_currency(
        self,
    ):
        result = (
            self.service.register_assignment(
                consumption_id=2,
                person_id=3,
                user_input="50%",
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
            result["assigned_cents"],
        )

        self.assertEqual(
            4000,
            result["pending_cents"],
        )

        self.assertIn(
            "Monto asignado: US$ 40.00",
            result["message"],
        )

    def test_rejects_amount_above_balance(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "superar el saldo pendiente",
        ):
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="101",
            )

        movements = (
            self.service
            .movimiento_repository
            .list_movements(1)
        )

        self.assertEqual(
            [],
            movements,
        )

    def test_rejects_assignment_when_completed(
        self,
    ):
        self.service.register_assignment(
            consumption_id=1,
            person_id=2,
            user_input="Todo",
        )

        with self.assertRaisesRegex(
            ValueError,
            "ya fue asignado completamente",
        ):
            self.service.register_assignment(
                consumption_id=1,
                person_id=1,
                user_input="10",
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )