import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.txt_service import TxtService


class GenerateAllTxtFilesTest(
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
                    "all-files-test-hash",
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
                (
                    1,
                    2,
                ),
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

    def test_generates_all_files(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        file_names = {
            path.name
            for path in result[
                "generated_paths"
            ]
        }

        self.assertEqual(
            {
                "Angel.txt",
                "Flor.txt",
                "Nayeli.txt",
                "Total.txt",
            },
            file_names,
        )

    def test_returns_correct_file_counts(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        self.assertEqual(
            3,
            result["person_file_count"],
        )

        self.assertEqual(
            1,
            result["total_file_count"],
        )

        self.assertEqual(
            4,
            result[
                "generated_file_count"
            ],
        )

    def test_all_generated_files_exist(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        for file_path in result[
            "generated_paths"
        ]:
            with self.subTest(
                file_name=file_path.name
            ):
                self.assertTrue(
                    file_path.exists()
                )

                self.assertTrue(
                    file_path.is_file()
                )

    def test_does_not_generate_empty_person(
        self,
    ):
        self.service.generate_all_files(
            estado_id=1
        )

        empty_file = (
            self.output_folder
            / "Sin movimientos.txt"
        )

        self.assertFalse(
            empty_file.exists()
        )

    def test_total_file_is_balanced(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        self.assertTrue(
            result["balanced"]
        )

        self.assertTrue(
            result["total_file"][
                "balanced"
            ]
        )

        total_path = (
            result["total_file"][
                "file_path"
            ]
        )

        total_content = (
            total_path.read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            (
                "COMPROBACIÓN CORRECTA: "
                "no existen diferencias."
            ),
            total_content,
        )

    def test_person_files_have_content(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        for person_file in result[
            "person_files"
        ]:
            file_path = (
                person_file["file_path"]
            )

            content = file_path.read_text(
                encoding="utf-8"
            )

            self.assertIn(
                (
                    "Persona: "
                    f"{person_file['person_name']}"
                ),
                content,
            )

            self.assertGreater(
                person_file[
                    "movement_count"
                ],
                0,
            )

    def test_total_contains_all_people(
        self,
    ):
        result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        total_content = (
            result["total_file"][
                "file_path"
            ].read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            "PERSONA: Angel",
            total_content,
        )

        self.assertIn(
            "PERSONA: Flor",
            total_content,
        )

        self.assertIn(
            "PERSONA: Nayeli",
            total_content,
        )

    def test_can_generate_files_again(
        self,
    ):
        first_result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        second_result = (
            self.service
            .generate_all_files(
                estado_id=1
            )
        )

        self.assertEqual(
            first_result[
                "generated_file_count"
            ],
            second_result[
                "generated_file_count"
            ],
        )

        self.assertEqual(
            4,
            second_result[
                "generated_file_count"
            ],
        )

        for file_path in second_result[
            "generated_paths"
        ]:
            self.assertTrue(
                file_path.exists()
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )