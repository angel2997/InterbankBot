import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.movimiento_asignacion_repository import (
    MovimientoAsignacionRepository,
)


class StatementMovementsTest(
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

        self._create_tables()
        self._insert_data()

        self.repository = (
            MovimientoAsignacionRepository()
        )

        self.repository.create_table()

    def tearDown(self):
        database_module.DB_PATH = (
            self.original_db_path
        )

        self.temporary_directory.cleanup()

    def _create_tables(self):
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

    def _insert_data(self):
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO estados_procesados (
                    periodo
                )
                VALUES (?)
                """,
                ("2026-07",),
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
                    ("Nayeli", 1),
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
                    asignacion,
                    persona_asignada,
                    persona_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        1,
                        "01-Jul",
                        "Consumo compartido",
                        10000,
                        0,
                        "Angel",
                        "PENDIENTE",
                        None,
                        None,
                    ),
                    (
                        1,
                        "02-Jul",
                        "Consumo automático",
                        5000,
                        0,
                        "Nayeli",
                        "AUTOMATICA",
                        "Nayeli",
                        3,
                    ),
                    (
                        1,
                        "03-Jul",
                        "Compra en dólares",
                        0,
                        3000,
                        "Angel",
                        "PENDIENTE",
                        None,
                        None,
                    ),
                ),
            )

    def test_lists_manual_movements(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=4000,
        )

        self.repository.add_movement(
            consumption_id=1,
            person_id=2,
            amount_cents=6000,
        )

        movements = (
            self.repository
            .list_movements_by_statement(
                estado_id=1
            )
        )

        manual_movements = [
            movement
            for movement in movements
            if movement["origen"]
            == "MOVIMIENTO"
        ]

        self.assertEqual(
            2,
            len(manual_movements),
        )

        self.assertEqual(
            {
                "Angel",
                "Flor",
            },
            {
                movement["persona"]
                for movement in manual_movements
            },
        )

    def test_includes_automatic_assignment(
        self,
    ):
        movements = (
            self.repository
            .list_movements_by_statement(
                estado_id=1
            )
        )

        automatic = [
            movement
            for movement in movements
            if movement["origen"]
            == "AUTOMATICA"
        ]

        self.assertEqual(
            1,
            len(automatic),
        )

        self.assertEqual(
            "Nayeli",
            automatic[0]["persona"],
        )

        self.assertEqual(
            "PEN",
            automatic[0]["moneda"],
        )

        self.assertEqual(
            5000,
            automatic[0]["monto_centimos"],
        )

    def test_keeps_repeated_movements(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=2000,
        )

        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=1000,
        )

        movements = (
            self.repository
            .list_movements_by_statement(
                estado_id=1
            )
        )

        angel_movements = [
            movement
            for movement in movements
            if movement["persona"] == "Angel"
        ]

        self.assertEqual(
            2,
            len(angel_movements),
        )

        self.assertEqual(
            [
                2000,
                1000,
            ],
            [
                movement["monto_centimos"]
                for movement in angel_movements
            ],
        )

    def test_preserves_dollar_currency(
        self,
    ):
        self.repository.add_movement(
            consumption_id=3,
            person_id=1,
            amount_cents=3000,
        )

        movements = (
            self.repository
            .list_movements_by_statement(
                estado_id=1
            )
        )

        dollar_movement = next(
            movement
            for movement in movements
            if movement["consumo_id"] == 3
        )

        self.assertEqual(
            "USD",
            dollar_movement["moneda"],
        )

        self.assertEqual(
            3000,
            dollar_movement[
                "monto_centimos"
            ],
        )

    def test_calculates_distributed_totals(
        self,
    ):
        self.repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=4000,
        )

        self.repository.add_movement(
            consumption_id=1,
            person_id=2,
            amount_cents=6000,
        )

        self.repository.add_movement(
            consumption_id=3,
            person_id=1,
            amount_cents=3000,
        )

        totals = (
            self.repository
            .get_distributed_totals(
                estado_id=1
            )
        )

        self.assertEqual(
            15000,
            totals["PEN"],
        )

        self.assertEqual(
            3000,
            totals["USD"],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )