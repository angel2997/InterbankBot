import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.txt_service import TxtService


class TxtServiceTest(unittest.TestCase):

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
            temporary_path / "test.db"
        )

        self.output_folder = (
            temporary_path / "txt"
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
                    fecha_correo TEXT,
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
                    "test-hash",
                    "estado-prueba.pdf",
                    "2026-09-12T10:00:00",
                    "PROCESADO",
                    185657,
                    0,
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
                    ("Sin movimientos", 1),
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
            amount_cents=2500,
        )

        repository.add_movement(
            consumption_id=1,
            person_id=1,
            amount_cents=1500,
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

    def _generate_files(self):
        return (
            self.service
            .generate_person_files(
                estado_id=1
            )
        )

    def _read_person_file(
        self,
        person_name,
    ):
        file_path = (
            self.output_folder
            / f"{person_name}.txt"
        )

        self.assertTrue(
            file_path.exists()
        )

        return file_path.read_text(
            encoding="utf-8"
        )

    def test_generates_one_file_per_person(
        self,
    ):
        generated = self._generate_files()

        file_names = {
            item["file_name"]
            for item in generated
        }

        self.assertEqual(
            {
                "Angel.txt",
                "Flor.txt",
                "Nayeli.txt",
            },
            file_names,
        )

    def test_does_not_generate_empty_person_file(
        self,
    ):
        self._generate_files()

        empty_file = (
            self.output_folder
            / "Sin movimientos.txt"
        )

        self.assertFalse(
            empty_file.exists()
        )

    def test_keeps_repeated_movements_separate(
        self,
    ):
        self._generate_files()

        content = self._read_person_file(
            "Angel"
        )

        self.assertIn(
            "Movimiento: 1",
            content,
        )

        self.assertIn(
            "Movimiento: 2",
            content,
        )

        self.assertIn(
            "Movimiento: 3",
            content,
        )

        repeated_description = (
            "Descripción: "
            "Consumo compartido"
        )

        self.assertEqual(
            2,
            content.count(
                repeated_description
            ),
        )

    def test_formats_soles_and_dollars(
        self,
    ):
        self._generate_files()

        content = self._read_person_file(
            "Angel"
        )

        self.assertIn(
            "Monto: S/ 25.00",
            content,
        )

        self.assertIn(
            "Monto: S/ 15.00",
            content,
        )

        self.assertIn(
            "Monto: US$ 30.00",
            content,
        )

        self.assertIn(
            "Total en soles: S/ 40.00",
            content,
        )

        self.assertIn(
            "Total en dólares: US$ 30.00",
            content,
        )

    def test_includes_person_and_period(
        self,
    ):
        self._generate_files()

        content = self._read_person_file(
            "Flor"
        )

        self.assertIn(
            "Periodo: 2026-07",
            content,
        )

        self.assertIn(
            "Persona: Flor",
            content,
        )

        self.assertIn(
            "Fecha: 01-Jul",
            content,
        )

        self.assertIn(
            "Descripción: Consumo compartido",
            content,
        )

        self.assertIn(
            "Monto: S/ 60.00",
            content,
        )

    def test_includes_automatic_nayeli_assignment(
        self,
    ):
        self._generate_files()

        content = self._read_person_file(
            "Nayeli"
        )

        self.assertIn(
            "Persona: Nayeli",
            content,
        )

        self.assertIn(
            "Descripción: Consumo automático",
            content,
        )

        self.assertIn(
            "Monto: S/ 50.00",
            content,
        )

        self.assertIn(
            "Total en soles: S/ 50.00",
            content,
        )

        self.assertIn(
            "Total en dólares: US$ 0.00",
            content,
        )

    def test_returns_generated_file_metadata(
        self,
    ):
        generated = self._generate_files()

        angel_result = next(
            item
            for item in generated
            if item["person_name"] == "Angel"
        )

        self.assertEqual(
            3,
            angel_result["movement_count"],
        )

        self.assertEqual(
            4000,
            angel_result[
                "total_pen_cents"
            ],
        )

        self.assertEqual(
            3000,
            angel_result[
                "total_usd_cents"
            ],
        )

        self.assertTrue(
            angel_result[
                "file_path"
            ].exists()
        )

    def test_writes_files_using_utf8(
        self,
    ):
        self._generate_files()

        content = self._read_person_file(
            "Nayeli"
        )

        self.assertIn(
            "Descripción",
            content,
        )

        self.assertIn(
            "dólares",
            content,
        )

        self.assertIn(
            "automático",
            content,
        )

    def test_rejects_statement_without_movements(
        self,
    ):
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO estados_procesados (
                    periodo,
                    hash_archivo,
                    nombre_pdf,
                    fecha_procesado,
                    estado
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "2026-08",
                    "second-test-hash",
                    "estado-vacio.pdf",
                    "2026-09-12T11:00:00",
                    "PROCESADO",
                ),
            )

        with self.assertRaisesRegex(
            LookupError,
            "No existen movimientos",
        ):
            (
                self.service
                .generate_person_files(
                    estado_id=2
                )
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )