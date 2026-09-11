import json

from database.db import get_connection


WAITING_PERSON = "ESPERANDO_PERSONA"
WAITING_NEW_PERSON_NAME = (
    "ESPERANDO_NOMBRE_NUEVO"
)
WAITING_AMOUNT = "ESPERANDO_MONTO"

VALID_CONVERSATION_STATES = {
    WAITING_PERSON,
    WAITING_NEW_PERSON_NAME,
    WAITING_AMOUNT,
}


class ConversationSessionRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    sesiones_conversacion (
                    numero_whatsapp TEXT
                        PRIMARY KEY,
                    estado_id INTEGER NOT NULL,
                    consumo_id INTEGER,
                    estado_conversacion
                        TEXT NOT NULL,
                    persona_id INTEGER,
                    persona_nombre TEXT,
                    opciones_json TEXT NOT NULL
                        DEFAULT '{}',
                    fecha_actualizacion
                        TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    CHECK (
                        estado_conversacion IN (
                            'ESPERANDO_PERSONA',
                            'ESPERANDO_NOMBRE_NUEVO',
                            'ESPERANDO_MONTO'
                        )
                    ),
                    FOREIGN KEY (estado_id)
                        REFERENCES
                            estados_procesados(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (consumo_id)
                        REFERENCES consumos(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (persona_id)
                        REFERENCES personas(id)
                        ON DELETE SET NULL
                )
                """
            )

    def save_session(
        self,
        whatsapp_number,
        estado_id,
        conversation_state,
        consumption_id=None,
        person_id=None,
        person_name=None,
        options=None,
    ):
        normalized_number = (
            self._normalize_whatsapp_number(
                whatsapp_number
            )
        )

        self._validate_conversation_state(
            conversation_state
        )

        normalized_options = (
            self._normalize_options(
                options
            )
        )

        options_json = json.dumps(
            normalized_options,
            ensure_ascii=False,
            sort_keys=True,
        )

        normalized_person_name = (
            self._normalize_optional_name(
                person_name
            )
        )

        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO sesiones_conversacion (
                    numero_whatsapp,
                    estado_id,
                    consumo_id,
                    estado_conversacion,
                    persona_id,
                    persona_nombre,
                    opciones_json,
                    fecha_actualizacion
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT(numero_whatsapp)
                DO UPDATE SET
                    estado_id = excluded.estado_id,
                    consumo_id = excluded.consumo_id,
                    estado_conversacion =
                        excluded.estado_conversacion,
                    persona_id = excluded.persona_id,
                    persona_nombre =
                        excluded.persona_nombre,
                    opciones_json =
                        excluded.opciones_json,
                    fecha_actualizacion =
                        CURRENT_TIMESTAMP
                """,
                (
                    normalized_number,
                    estado_id,
                    consumption_id,
                    conversation_state,
                    person_id,
                    normalized_person_name,
                    options_json,
                ),
            )

        return self.get_session(
            normalized_number
        )

    def get_session(
        self,
        whatsapp_number,
    ):
        normalized_number = (
            self._normalize_whatsapp_number(
                whatsapp_number
            )
        )

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    numero_whatsapp,
                    estado_id,
                    consumo_id,
                    estado_conversacion,
                    persona_id,
                    persona_nombre,
                    opciones_json,
                    fecha_actualizacion
                FROM sesiones_conversacion
                WHERE numero_whatsapp = ?
                """,
                (normalized_number,),
            ).fetchone()

        if row is None:
            return None

        session = dict(row)

        session["opciones"] = json.loads(
            session.pop("opciones_json")
        )

        return session

    def update_conversation_state(
        self,
        whatsapp_number,
        conversation_state,
        consumption_id=None,
        person_id=None,
        person_name=None,
        options=None,
    ):
        normalized_number = (
            self._normalize_whatsapp_number(
                whatsapp_number
            )
        )

        current_session = self.get_session(
            normalized_number
        )

        if current_session is None:
            raise LookupError(
                "No existe una sesión para "
                "el número indicado"
            )

        if options is None:
            options = current_session[
                "opciones"
            ]

        return self.save_session(
            whatsapp_number=normalized_number,
            estado_id=current_session[
                "estado_id"
            ],
            conversation_state=(
                conversation_state
            ),
            consumption_id=consumption_id,
            person_id=person_id,
            person_name=person_name,
            options=options,
        )

    def delete_session(
        self,
        whatsapp_number,
    ):
        normalized_number = (
            self._normalize_whatsapp_number(
                whatsapp_number
            )
        )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM sesiones_conversacion
                WHERE numero_whatsapp = ?
                """,
                (normalized_number,),
            )

        return cursor.rowcount == 1

    def count_sessions(self):
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM sesiones_conversacion
                """
            ).fetchone()

        return row["total"]

    @staticmethod
    def _normalize_whatsapp_number(
        whatsapp_number,
    ):
        normalized_number = "".join(
            str(whatsapp_number).split()
        )

        if not normalized_number:
            raise ValueError(
                "El número de WhatsApp "
                "es obligatorio"
            )

        if normalized_number.startswith(
            "+"
        ):
            digits = normalized_number[1:]
        else:
            digits = normalized_number

        if not digits.isdigit():
            raise ValueError(
                "El número de WhatsApp solo "
                "puede contener dígitos y "
                "un signo + inicial"
            )

        return normalized_number

    @staticmethod
    def _validate_conversation_state(
        conversation_state,
    ):
        if (
            conversation_state
            not in VALID_CONVERSATION_STATES
        ):
            raise ValueError(
                "Estado de conversación "
                "no válido"
            )

    @staticmethod
    def _normalize_options(
        options,
    ):
        if options is None:
            return {}

        if not isinstance(options, dict):
            raise TypeError(
                "Las opciones deben enviarse "
                "como un diccionario"
            )

        return {
            str(key): str(value)
            for key, value in options.items()
        }

    @staticmethod
    def _normalize_optional_name(
        person_name,
    ):
        if person_name is None:
            return None

        normalized_name = " ".join(
            str(person_name).split()
        )

        if not normalized_name:
            return None

        return normalized_name