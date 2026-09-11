import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.movimiento_asignacion_repository import (
    MovimientoAsignacionRepository,
)


class AssignmentMovementsTest(
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

        self.repository = (
            MovimientoAsignacionRepository()
        )

        self.repository.create_table()

        self._insert_test_data()

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
                    ("Temporal ajeno", 0),
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
                    (1, 0, 4570),
                ),
            )

    def test_saves_two_movements_for_same_person(
        self,
    ):
        first_id = (
            self.repository.add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=2000,
            )
        )

        second_id = (
            self.repository.add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=1000,
            )
        )

        movements = (
            self.repository.list_movements(1)
        )

        self.assertNotEqual(
            first_id,
            second_id,
        )

        self.assertEqual(
            2,
            len(movements),
        )

        movement_amounts = [
            item["monto_centimos"]
            for item in movements
        ]

        self.assertEqual(
            [2000, 1000],
            movement_amounts,
        )

    def test_calculates_pending_balance(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=2500,
        )

        self.repository.add_movement(
            consumption_id=1,
            person_id=2,
            amount_cents=3000,
        )

        balance = (
            self.repository.get_balance(1)
        )

        self.assertEqual(
            "PEN",
            balance["currency"],
        )

        self.assertEqual(
            10000,
            balance["total_cents"],
        )

        self.assertEqual(
            5500,
            balance["assigned_cents"],
        )

        self.assertEqual(
            4500,
            balance["pending_cents"],
        )

        self.assertFalse(
            balance["completed"]
        )

    def test_marks_consumption_completed_at_zero_balance(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=2,
            amount_cents=10000,
        )

        balance = (
            self.repository.get_balance(1)
        )

        self.assertEqual(
            0,
            balance["pending_cents"],
        )

        self.assertTrue(
            balance["completed"]
        )

    def test_preserves_dollar_currency(
        self,
    ):
        self.repository.add_movement(
            consumption_id=2,
            person_id=2,
            amount_cents=2000,
        )

        balance = (
            self.repository.get_balance(2)
        )

        movements = (
            self.repository.list_movements(2)
        )

        movement = movements[0]

        self.assertEqual(
            "USD",
            balance["currency"],
        )

        self.assertEqual(
            "USD",
            movement["moneda"],
        )

        self.assertEqual(
            2570,
            balance["pending_cents"],
        )

    def test_rejects_amount_above_pending_balance(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=8000,
        )

        with self.assertRaisesRegex(
            ValueError,
            "superar el saldo pendiente",
        ):
            self.repository.add_movement(
                consumption_id=1,
                person_id=2,
                amount_cents=2001,
            )

    def test_allows_permanent_person(
        self,
    ):
        movement_id = (
            self.repository.add_movement(
                consumption_id=1,
                person_id=2,
                amount_cents=1000,
            )
        )

        self.assertGreater(
            movement_id,
            0,
        )

    def test_rejects_temporary_person_from_other_statement(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "no esta disponible",
        ):
            self.repository.add_movement(
                consumption_id=1,
                person_id=3,
                amount_cents=1000,
            )

    def test_deletes_only_last_movement(
        self,
    ):
        first_id = (
            self.repository.add_movement(
                consumption_id=1,
                person_id=1,
                amount_cents=2000,
            )
        )

        second_id = (
            self.repository.add_movement(
                consumption_id=1,
                person_id=2,
                amount_cents=3000,
            )
        )

        deleted = (
            self.repository
            .delete_last_movement(1)
        )

        movements = (
            self.repository.list_movements(1)
        )

        balance = (
            self.repository.get_balance(1)
        )

        self.assertEqual(
            second_id,
            deleted["id"],
        )

        self.assertEqual(
            "Angel",
            deleted["persona"],
        )

        remaining_ids = [
            item["id"]
            for item in movements
        ]

        self.assertEqual(
            [first_id],
            remaining_ids,
        )

        self.assertEqual(
            8000,
            balance["pending_cents"],
        )

    def test_rejects_delete_when_no_movements_exist(
        self,
    ):
        with self.assertRaisesRegex(
            LookupError,
            "no tiene asignaciones",
        ):
            (
                self.repository
                .delete_last_movement(1)
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )