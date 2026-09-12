import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.txt_service import TxtService


class TotalTxtServiceTest(
    unittest.TestCase
):

    def setUp(self):
        self.temporary_directory = (
            tempfile.TemporaryDirectory()
        )

        self.original_db_path = (
            database_module.DB_PATH
        )

        temporary_path = Path(
            self.temporary_directory.name
        )

        database_module.DB_PATH = (
            temporary_path
            / "test.db"
        )

        self.output_folder = (
            temporary_path
            / "txt"
        )

        self._create_tables()
        self._insert_data()

        self.service = TxtService(
            output_folder=self.output_folder
        )

        (
            self.service
            .movimiento_repository
            .create_table()
        )

        self._insert_movements()

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
                    periodo TEXT,
                    hash_archivo TEXT
                        NOT NULL UNIQUE,
                    nombre_pdf TEXT NOT NULL,
                    fecha_procesado TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    pago_mes_soles_centimos INTEGER,
                    pago_mes_dolares_centimos INTEGER,
                    seguro_desgravamen_soles_centimos
                        INTEGER,
                    seguro_desgravamen_dolares_centimos
                        INTEGER
                );

                CREATE TABLE personas (
                    id INTEGER
                        PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL
                        COLLATE NOCASE UNIQUE,
                    permanente INTEGER NOT NULL
                );

                CREATE TABLE estado_personas (
                    estado_id INTEGER NOT NULL,
                    persona_id INTEGER NOT NULL,
                    PRIMARY KEY (
                        estado_id,
                        persona_id
                    )
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
                    persona_id INTEGER
                );
                """
            )

    def _insert_data(self):
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO estados_procesados (
                    periodo,
                    hash_archivo,
                    nombre_pdf,
                    fecha_procesado,
                    estado,
                    pago_mes_soles_centimos,
                    pago_mes_dolares_centimos,
                    seguro_desgravamen_soles_centimos,
                    seguro_desgravamen_dolares_centimos
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-07",
                    "total-test-hash",
                    "estado-prueba.pdf",
                    "2026-09-12T10:00:00",
                    "PROCESADO",
                    16262,
                    3000,
                    1262,
                    0,
                ),
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

    def _insert_movements(self):
        repository = (
            self.service
            .movimiento_repository
        )

        repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=4000,
        )

        repository.add_movement(
            consumption_id=1,
            person_id=2,
            amount_cents=6000,
        )

        repository.add_movement(
            consumption_id=3,
            person_id=1,
            amount_cents=3000,
        )

    def _generate_total(self):
        return (
            self.service
            .generate_total_file(
                estado_id=1
            )
        )

    def _read_total(self):
        file_path = (
            self.output_folder
            / "Total.txt"
        )

        self.assertTrue(
            file_path.exists()
        )

        return file_path.read_text(
            encoding="utf-8"
        )

    def test_generates_total_file(
        self,
    ):
        result = self._generate_total()

        self.assertEqual(
            "Total.txt",
            result["file_name"],
        )

        self.assertTrue(
            result["file_path"].exists()
        )

    def test_includes_payment_from_pdf(
        self,
    ):
        self._generate_total()
        content = self._read_total()

        self.assertIn(
            "PAGO DEL MES SEGÚN PDF",
            content,
        )

        self.assertIn(
            "Soles: S/ 162.62",
            content,
        )

        self.assertIn(
            "Dólares: US$ 30.00",
            content,
        )

    def test_includes_distributed_totals(
        self,
    ):
        result = self._generate_total()
        content = self._read_total()

        self.assertEqual(
            15000,
            result[
                "distributed_pen_cents"
            ],
        )

        self.assertEqual(
            3000,
            result[
                "distributed_usd_cents"
            ],
        )

        self.assertIn(
            (
                "TOTAL DISTRIBUIDO "
                "ENTRE PERSONAS"
            ),
            content,
        )

        self.assertIn(
            "Soles: S/ 150.00",
            content,
        )

    def test_includes_insurance(
        self,
    ):
        result = self._generate_total()
        content = self._read_total()

        self.assertEqual(
            1262,
            result[
                "insurance_pen_cents"
            ],
        )

        self.assertIn(
            "SEGURO DE DESGRAVAMEN",
            content,
        )

        self.assertIn(
            "Soles: S/ 12.62",
            content,
        )

    def test_has_zero_difference(
        self,
    ):
        result = self._generate_total()
        content = self._read_total()

        self.assertEqual(
            0,
            result[
                "difference_pen_cents"
            ],
        )

        self.assertEqual(
            0,
            result[
                "difference_usd_cents"
            ],
        )

        self.assertTrue(
            result["balanced"]
        )

        self.assertIn(
            (
                "COMPROBACIÓN CORRECTA: "
                "no existen diferencias."
            ),
            content,
        )

    def test_includes_person_details(
        self,
    ):
        self._generate_total()
        content = self._read_total()

        self.assertIn(
            "PERSONA: Angel",
            content,
        )

        self.assertIn(
            "PERSONA: Flor",
            content,
        )

        self.assertIn(
            "PERSONA: Nayeli",
            content,
        )

        self.assertIn(
            "Monto: S/ 40.00",
            content,
        )

        self.assertIn(
            "Monto: US$ 30.00",
            content,
        )

        self.assertIn(
            "Monto: S/ 60.00",
            content,
        )

        self.assertIn(
            "Monto: S/ 50.00",
            content,
        )

    def test_returns_counts(
        self,
    ):
        result = self._generate_total()

        self.assertEqual(
            3,
            result["person_count"],
        )

        self.assertEqual(
            4,
            result["movement_count"],
        )

    def test_warns_when_difference_exists(
        self,
    ):
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE estados_procesados
                SET pago_mes_soles_centimos = ?
                WHERE id = ?
                """,
                (
                    17000,
                    1,
                ),
            )

        result = self._generate_total()
        content = self._read_total()

        self.assertFalse(
            result["balanced"]
        )

        self.assertEqual(
            738,
            result[
                "difference_pen_cents"
            ],
        )

        self.assertIn(
            (
                "ADVERTENCIA: existe una "
                "diferencia pendiente "
                "de revisión."
            ),
            content,
        )

        self.assertIn(
            "Soles: S/ 7.38",
            content,
        )

    def test_rejects_missing_summary(
        self,
    ):
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE estados_procesados
                SET pago_mes_soles_centimos = NULL
                WHERE id = ?
                """,
                (1,),
            )

        with self.assertRaisesRegex(
            ValueError,
            "no tiene guardado",
        ):
            self._generate_total()


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )