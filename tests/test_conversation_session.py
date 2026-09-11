import tempfile
import unittest
from pathlib import Path

import database.db as database_module
from database.db import get_connection
from repositories.conversation_session_repository import (
    ConversationSessionRepository,
)
from repositories.conversation_session_repository import (
    WAITING_AMOUNT,
)
from repositories.conversation_session_repository import (
    WAITING_NEW_PERSON_NAME,
)
from repositories.conversation_session_repository import (
    WAITING_PERSON,
)


class ConversationSessionTest(
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

        self.repository = (
            ConversationSessionRepository()
        )

        self.repository.create_table()

        self.whatsapp_number = (
            "+51999999999"
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

            connection.execute(
                """
                INSERT INTO personas (
                    nombre,
                    permanente
                )
                VALUES (?, ?)
                """,
                (
                    "Angel",
                    1,
                ),
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

    def test_creates_session(
        self,
    ):
        session = (
            self.repository.save_session(
                whatsapp_number=(
                    self.whatsapp_number
                ),
                estado_id=1,
                conversation_state=(
                    WAITING_PERSON
                ),
                consumption_id=1,
                options={
                    "1": "Angel",
                    "2": "__NEW_PERSON__",
                },
            )
        )

        self.assertEqual(
            self.whatsapp_number,
            session["numero_whatsapp"],
        )

        self.assertEqual(
            1,
            session["estado_id"],
        )

        self.assertEqual(
            1,
            session["consumo_id"],
        )

        self.assertEqual(
            WAITING_PERSON,
            session[
                "estado_conversacion"
            ],
        )

        self.assertIsNone(
            session["persona_id"]
        )

        self.assertIsNone(
            session["persona_nombre"]
        )

    def test_saves_and_recovers_options(
        self,
    ):
        expected_options = {
            "1": "Angel",
            "2": "Flor",
            "3": "__NEW_PERSON__",
        }

        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
            options=expected_options,
        )

        session = (
            self.repository.get_session(
                self.whatsapp_number
            )
        )

        self.assertEqual(
            expected_options,
            session["opciones"],
        )

    def test_updates_existing_session(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
            options={
                "1": "Angel",
                "2": "__NEW_PERSON__",
            },
        )

        updated = (
            self.repository
            .update_conversation_state(
                whatsapp_number=(
                    self.whatsapp_number
                ),
                conversation_state=(
                    WAITING_NEW_PERSON_NAME
                ),
                consumption_id=1,
                options={},
            )
        )

        self.assertEqual(
            WAITING_NEW_PERSON_NAME,
            updated[
                "estado_conversacion"
            ],
        )

        self.assertEqual(
            {},
            updated["opciones"],
        )

        self.assertEqual(
            1,
            self.repository.count_sessions(),
        )

    def test_saves_selected_person(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
            options={
                "1": "Angel",
            },
        )

        updated = (
            self.repository
            .update_conversation_state(
                whatsapp_number=(
                    self.whatsapp_number
                ),
                conversation_state=(
                    WAITING_AMOUNT
                ),
                consumption_id=1,
                person_id=1,
                person_name="Angel",
                options={},
            )
        )

        self.assertEqual(
            WAITING_AMOUNT,
            updated[
                "estado_conversacion"
            ],
        )

        self.assertEqual(
            1,
            updated["persona_id"],
        )

        self.assertEqual(
            "Angel",
            updated["persona_nombre"],
        )

    def test_keeps_one_session_per_number(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
        )

        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_AMOUNT
            ),
            consumption_id=1,
            person_id=1,
            person_name="Angel",
        )

        self.assertEqual(
            1,
            self.repository.count_sessions(),
        )

        session = (
            self.repository.get_session(
                self.whatsapp_number
            )
        )

        self.assertEqual(
            WAITING_AMOUNT,
            session[
                "estado_conversacion"
            ],
        )

    def test_recovers_session_with_new_repository(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_AMOUNT
            ),
            consumption_id=1,
            person_id=1,
            person_name="Angel",
        )

        new_repository = (
            ConversationSessionRepository()
        )

        recovered = (
            new_repository.get_session(
                self.whatsapp_number
            )
        )

        self.assertIsNotNone(
            recovered
        )

        self.assertEqual(
            WAITING_AMOUNT,
            recovered[
                "estado_conversacion"
            ],
        )

        self.assertEqual(
            "Angel",
            recovered[
                "persona_nombre"
            ],
        )

    def test_deletes_session(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
        )

        deleted = (
            self.repository.delete_session(
                self.whatsapp_number
            )
        )

        recovered = (
            self.repository.get_session(
                self.whatsapp_number
            )
        )

        self.assertTrue(
            deleted
        )

        self.assertIsNone(
            recovered
        )

        self.assertEqual(
            0,
            self.repository.count_sessions(),
        )

    def test_rejects_unknown_state(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "no válido",
        ):
            self.repository.save_session(
                whatsapp_number=(
                    self.whatsapp_number
                ),
                estado_id=1,
                conversation_state=(
                    "ESTADO_DESCONOCIDO"
                ),
                consumption_id=1,
            )

        self.assertEqual(
            0,
            self.repository.count_sessions(),
        )

    def test_rejects_invalid_whatsapp_number(
        self,
    ):
        invalid_numbers = (
            "",
            "   ",
            "+51ABC123",
            "999-999-999",
        )

        for invalid_number in (
            invalid_numbers
        ):
            with self.subTest(
                number=invalid_number
            ):
                with self.assertRaises(
                    ValueError
                ):
                    (
                        self.repository
                        .save_session(
                            whatsapp_number=(
                                invalid_number
                            ),
                            estado_id=1,
                            conversation_state=(
                                WAITING_PERSON
                            ),
                            consumption_id=1,
                        )
                    )

    def test_normalizes_number_spaces(
        self,
    ):
        session = (
            self.repository.save_session(
                whatsapp_number=(
                    "+51 999 999 999"
                ),
                estado_id=1,
                conversation_state=(
                    WAITING_PERSON
                ),
                consumption_id=1,
            )
        )

        self.assertEqual(
            "+51999999999",
            session["numero_whatsapp"],
        )

    def test_normalizes_person_name_spaces(
        self,
    ):
        self.repository.save_session(
            whatsapp_number=(
                self.whatsapp_number
            ),
            estado_id=1,
            conversation_state=(
                WAITING_PERSON
            ),
            consumption_id=1,
        )

        session = (
            self.repository
            .update_conversation_state(
                whatsapp_number=(
                    self.whatsapp_number
                ),
                conversation_state=(
                    WAITING_AMOUNT
                ),
                consumption_id=1,
                person_id=1,
                person_name=(
                    "  Angel   Quispe  "
                ),
            )
        )

        self.assertEqual(
            "Angel Quispe",
            session["persona_nombre"],
        )

    def test_update_rejects_missing_session(
        self,
    ):
        with self.assertRaisesRegex(
            LookupError,
            "No existe una sesión",
        ):
            (
                self.repository
                .update_conversation_state(
                    whatsapp_number=(
                        self.whatsapp_number
                    ),
                    conversation_state=(
                        WAITING_AMOUNT
                    ),
                    consumption_id=1,
                    person_id=1,
                    person_name="Angel",
                )
            )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )