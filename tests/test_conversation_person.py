import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from services.conversation_service import (
    ConversationService,
)


class ConversationPersonTest(
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

        self.options = {
            "1": "Angel",
            "2": "Flor",
            "3": "__NEW_PERSON__",
        }

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
                        DEFAULT 1
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
                            estados_procesados(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                        ON DELETE CASCADE
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
                        ON DELETE CASCADE
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
                    monto_soles_centimos,
                    monto_dolares_centimos
                )
                VALUES (?, ?, ?)
                """,
                (
                    1,
                    10000,
                    0,
                ),
            )

    def test_selects_existing_person(
        self,
    ):
        result = (
            self.service
            .process_person_selection(
                estado_id=1,
                consumption_id=1,
                selected_option="1",
                options=self.options,
            )
        )

        self.assertTrue(
            result["valid"]
        )

        self.assertEqual(
            "request_amount",
            result["action"],
        )

        self.assertEqual(
            1,
            result["person_id"],
        )

        self.assertEqual(
            "Angel",
            result["person_name"],
        )

        self.assertEqual(
            10000,
            result["pending_cents"],
        )

        self.assertIn(
            "¿Cuánto deseas asignar a Angel?",
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

    def test_selects_temporary_person(
        self,
    ):
        result = (
            self.service
            .process_person_selection(
                estado_id=1,
                consumption_id=1,
                selected_option="2",
                options=self.options,
            )
        )

        self.assertEqual(
            2,
            result["person_id"],
        )

        self.assertEqual(
            "Flor",
            result["person_name"],
        )

        self.assertEqual(
            "request_amount",
            result["action"],
        )

    def test_detects_new_person_option(
        self,
    ):
        result = (
            self.service
            .process_person_selection(
                estado_id=1,
                consumption_id=1,
                selected_option="3",
                options=self.options,
            )
        )

        self.assertTrue(
            result["valid"]
        )

        self.assertEqual(
            "request_new_person_name",
            result["action"],
        )

        self.assertIn(
            "Escribe el nombre",
            result["message"],
        )

        self.assertIsNone(
            result["person_id"]
        )

    def test_rejects_invalid_option(
        self,
    ):
        result = (
            self.service
            .process_person_selection(
                estado_id=1,
                consumption_id=1,
                selected_option="8",
                options=self.options,
            )
        )

        self.assertFalse(
            result["valid"]
        )

        self.assertEqual(
            "invalid_option",
            result["action"],
        )

        self.assertIn(
            "no es válida",
            result["message"],
        )

    def test_creates_temporary_person(
        self,
    ):
        result = (
            self.service
            .create_temporary_person(
                estado_id=1,
                consumption_id=1,
                person_name="Carlos",
            )
        )

        self.assertTrue(
            result["created"]
        )

        self.assertEqual(
            "request_amount",
            result["action"],
        )

        self.assertEqual(
            "Carlos",
            result["person_name"],
        )

        self.assertIn(
            (
                "Carlos fue agregado "
                "como persona temporal."
            ),
            result["message"],
        )

        self.assertIn(
            "Saldo pendiente: S/ 100.00",
            result["message"],
        )

        person = (
            self.service
            .persona_repository
            .find_by_name(
                "Carlos"
            )
        )

        self.assertIsNotNone(
            person
        )

        self.assertEqual(
            0,
            person["permanente"],
        )

        with get_connection() as connection:
            relation = connection.execute(
                """
                SELECT
                    estado_id,
                    persona_id
                FROM estado_personas
                WHERE estado_id = ?
                  AND persona_id = ?
                """,
                (
                    1,
                    person["id"],
                ),
            ).fetchone()

        self.assertIsNotNone(
            relation
        )

    def test_normalizes_person_name_spaces(
        self,
    ):
        result = (
            self.service
            .create_temporary_person(
                estado_id=1,
                consumption_id=1,
                person_name=(
                    "  Carlos   Alberto  "
                ),
            )
        )

        self.assertEqual(
            "Carlos Alberto",
            result["person_name"],
        )

    def test_warns_when_person_already_exists(
        self,
    ):
        result = (
            self.service
            .create_temporary_person(
                estado_id=1,
                consumption_id=1,
                person_name="Angel",
            )
        )

        self.assertFalse(
            result["created"]
        )

        self.assertEqual(
            "person_already_exists",
            result["action"],
        )

        self.assertEqual(
            "Angel",
            result["person_name"],
        )

        self.assertIn(
            (
                'La persona "Angel" '
                "ya existe."
            ),
            result["message"],
        )

    def test_duplicate_check_ignores_uppercase(
        self,
    ):
        result = (
            self.service
            .create_temporary_person(
                estado_id=1,
                consumption_id=1,
                person_name="flor",
            )
        )

        self.assertFalse(
            result["created"]
        )

        self.assertEqual(
            "person_already_exists",
            result["action"],
        )

        self.assertEqual(
            "Flor",
            result["person_name"],
        )

    def test_rejects_empty_person_name(
        self,
    ):
        result = (
            self.service
            .create_temporary_person(
                estado_id=1,
                consumption_id=1,
                person_name="   ",
            )
        )

        self.assertFalse(
            result["created"]
        )

        self.assertEqual(
            "request_new_person_name",
            result["action"],
        )

        self.assertIn(
            "no puede estar vacío",
            result["message"],
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )