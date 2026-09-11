import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.asignacion_repository import (
    AsignacionRepository,
)
from repositories.movimiento_asignacion_repository import (
    MovimientoAsignacionRepository,
)


class PendingWithMovementsTest(
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

        self.asignacion_repository = (
            AsignacionRepository()
        )

        self.movimiento_repository = (
            MovimientoAsignacionRepository()
        )

        self.movimiento_repository.create_table()

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
                    (
                        1,
                        "03-Ago",
                        "Consumo de Nayeli",
                        5000,
                        0,
                        "Nayeli",
                        "AUTOMATICA",
                    ),
                ),
            )

    def test_lists_consumption_without_movements(
        self,
    ):
        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        self.assertEqual(
            2,
            len(pending),
        )

        soles_consumption = pending[0]

        self.assertEqual(
            "PEN",
            soles_consumption["moneda"],
        )

        self.assertEqual(
            10000,
            soles_consumption[
                "total_centimos"
            ],
        )

        self.assertEqual(
            0,
            soles_consumption[
                "asignado_centimos"
            ],
        )

        self.assertEqual(
            10000,
            soles_consumption[
                "pendiente_centimos"
            ],
        )

    def test_lists_partially_assigned_consumption(
        self,
    ):
        self.movimiento_repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=4000,
        )

        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        soles_consumption = pending[0]

        self.assertEqual(
            4000,
            soles_consumption[
                "asignado_centimos"
            ],
        )

        self.assertEqual(
            6000,
            soles_consumption[
                "pendiente_centimos"
            ],
        )

        self.assertEqual(
            60.0,
            soles_consumption[
                "saldo_pendiente"
            ],
        )

    def test_excludes_completed_consumption(
        self,
    ):
        self.movimiento_repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=10000,
        )

        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        pending_ids = [
            consumption["id"]
            for consumption in pending
        ]

        self.assertNotIn(
            1,
            pending_ids,
        )

        self.assertIn(
            2,
            pending_ids,
        )

    def test_consumption_returns_after_undo(
        self,
    ):
        self.movimiento_repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=10000,
        )

        pending_before_undo = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        ids_before_undo = [
            consumption["id"]
            for consumption
            in pending_before_undo
        ]

        self.assertNotIn(
            1,
            ids_before_undo,
        )

        (
            self.movimiento_repository
            .delete_last_movement(
                consumption_id=1
            )
        )

        pending_after_undo = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        ids_after_undo = [
            consumption["id"]
            for consumption
            in pending_after_undo
        ]

        self.assertIn(
            1,
            ids_after_undo,
        )

        restored_consumption = next(
            consumption
            for consumption
            in pending_after_undo
            if consumption["id"] == 1
        )

        self.assertEqual(
            10000,
            restored_consumption[
                "pendiente_centimos"
            ],
        )

    def test_preserves_dollar_currency(
        self,
    ):
        self.movimiento_repository.add_movement(
            consumption_id=2,
            person_id=3,
            amount_cents=3000,
        )

        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        dollar_consumption = next(
            consumption
            for consumption in pending
            if consumption["id"] == 2
        )

        self.assertEqual(
            "USD",
            dollar_consumption["moneda"],
        )

        self.assertEqual(
            8000,
            dollar_consumption[
                "total_centimos"
            ],
        )

        self.assertEqual(
            3000,
            dollar_consumption[
                "asignado_centimos"
            ],
        )

        self.assertEqual(
            5000,
            dollar_consumption[
                "pendiente_centimos"
            ],
        )

        self.assertEqual(
            50.0,
            dollar_consumption[
                "saldo_pendiente"
            ],
        )

    def test_excludes_nayeli_consumptions(
        self,
    ):
        pending = (
            self.asignacion_repository
            .list_pending_angel_consumptions(
                estado_id=1
            )
        )

        pending_ids = [
            consumption["id"]
            for consumption in pending
        ]

        self.assertNotIn(
            3,
            pending_ids,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )