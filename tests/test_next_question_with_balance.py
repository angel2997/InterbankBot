import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.conversation_service import (
    ConversationService,
)


class NextQuestionWithBalanceTest(
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
                (1, 2),
            )

            connection.executemany(
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
                    (
                        1,
                        "01-Ago",
                        "Consumo en soles",
                        10000,
                        0,
                        "Angel",
                        "PENDIENTE",
                    ),
                    (
                        1,
                        "02-Ago",
                        "Consumo en dólares",
                        0,
                        8000,
                        "Angel",
                        "PENDIENTE",
                    ),
                ),
            )

    def test_displays_soles_balance(
        self,
    ):
        result = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertEqual(
            "PEN",
            result["currency"],
        )

        self.assertEqual(
            "S/",
            result["currency_symbol"],
        )

        self.assertEqual(
            10000,
            result["total_cents"],
        )

        self.assertEqual(
            0,
            result["assigned_cents"],
        )

        self.assertEqual(
            10000,
            result["pending_cents"],
        )

        self.assertIn(
            "Monto total: S/ 100.00",
            result["message"],
        )

        self.assertIn(
            "Monto asignado: S/ 0.00",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

    def test_displays_partial_balance(
        self,
    ):
        (
            self.service
            .movimiento_repository
            .add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=4000,
            )
        )

        result = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertEqual(
            4000,
            result["assigned_cents"],
        )

        self.assertEqual(
            6000,
            result["pending_cents"],
        )

        self.assertIn(
            "Monto asignado: S/ 40.00",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 60.00",
            result["message"],
        )

    def test_shows_undo_only_when_movement_exists(
        self,
    ):
        result_without_movement = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertFalse(
            result_without_movement[
                "can_undo"
            ]
        )

        self.assertNotIn(
            'Escribe "Deshacer"',
            result_without_movement[
                "message"
            ],
        )

        (
            self.service
            .movimiento_repository
            .add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=2500,
            )
        )

        result_with_movement = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertTrue(
            result_with_movement[
                "can_undo"
            ]
        )

        self.assertIn(
            'Escribe "Deshacer"',
            result_with_movement[
                "message"
            ],
        )

    def test_includes_people_and_new_person(
        self,
    ):
        result = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertEqual(
            "Angel",
            result["options"]["1"],
        )

        self.assertEqual(
            "Fernando",
            result["options"]["2"],
        )

        self.assertEqual(
            "Flor",
            result["options"]["3"],
        )

        self.assertEqual(
            "__NEW_PERSON__",
            result["options"]["4"],
        )

        self.assertIn(
            "1. Angel",
            result["message"],
        )

        self.assertIn(
            "2. Fernando",
            result["message"],
        )

        self.assertIn(
            "3. Flor (temporal)",
            result["message"],
        )

        self.assertIn(
            "4. Nueva persona",
            result["message"],
        )

    def test_advances_to_dollar_consumption(
        self,
    ):
        (
            self.service
            .movimiento_repository
            .add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=10000,
            )
        )

        result = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertFalse(
            result["completed"]
        )

        self.assertEqual(
            2,
            result["consumption"]["id"],
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
            8000,
            result["total_cents"],
        )

        self.assertEqual(
            0,
            result["assigned_cents"],
        )

        self.assertEqual(
            8000,
            result["pending_cents"],
        )

        self.assertIn(
            "Descripción: Consumo en dólares",
            result["message"],
        )

        self.assertIn(
            "Monto total: US$ 80.00",
            result["message"],
        )

        self.assertIn(
            "Monto asignado: US$ 0.00",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: US$ 80.00",
            result["message"],
        )

    def test_completes_when_all_consumptions_assigned(
        self,
    ):
        (
            self.service
            .movimiento_repository
            .add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=10000,
            )
        )

        (
            self.service
            .movimiento_repository
            .add_movement(
                consumption_id=2,
                person_id=3,
                amount_cents=8000,
            )
        )

        result = (
            self.service
            .build_next_question(
                estado_id=1
            )
        )

        self.assertTrue(
            result["completed"]
        )

        self.assertIsNone(
            result["consumption"]
        )

        self.assertEqual(
            {},
            result["options"],
        )

        self.assertEqual(
            (
                "Todos los consumos "
                "fueron asignados."
            ),
            result["message"],
        )
if __name__=="__main__":
    unittest.main(
        verbosity=2
    )
