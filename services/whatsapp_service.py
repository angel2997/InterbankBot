import os

from dotenv import load_dotenv

from services.conversation_engine_service import (
    ConversationEngineService,
)


class WhatsappService:

    def __init__(
        self,
        allowed_number=None,
        conversation_engine=None,
    ):
        load_dotenv()

        configured_number = (
            allowed_number
            or os.getenv(
                "WHATSAPP_ALLOWED_NUMBER"
            )
        )

        self.allowed_number = (
            self._normalize_number(
                configured_number
            )
        )

        self.conversation_engine = (
            conversation_engine
            or ConversationEngineService()
        )

    def prepare_tables(self):
        (
            self.conversation_engine
            .conversation_service
            .movimiento_repository
            .create_table()
        )

        (
            self.conversation_engine
            .session_repository
            .create_table()
        )

    def start_conversation(
        self,
        whatsapp_number,
        estado_id,
    ):
        normalized_number = (
            self._validate_authorized_number(
                whatsapp_number
            )
        )

        return (
            self.conversation_engine
            .start_conversation(
                whatsapp_number=(
                    normalized_number
                ),
                estado_id=estado_id,
            )
        )

    def receive_message(
        self,
        whatsapp_number,
        message,
    ):
        normalized_number = (
            self._validate_authorized_number(
                whatsapp_number
            )
        )

        normalized_message = str(
            message
        ).strip()

        if not normalized_message:
            return {
                "accepted": False,
                "action": "empty_message",
                "completed": False,
                "message": (
                    "El mensaje no puede "
                    "estar vacío."
                ),
            }

        try:
            result = (
                self.conversation_engine
                .process_message(
                    whatsapp_number=(
                        normalized_number
                    ),
                    message=normalized_message,
                )
            )

        except LookupError as error:
            return {
                "accepted": False,
                "action": "no_active_conversation",
                "completed": False,
                "message": str(error),
            }

        return {
            "accepted": True,
            **result,
        }

    def get_active_session(
        self,
        whatsapp_number,
    ):
        normalized_number = (
            self._validate_authorized_number(
                whatsapp_number
            )
        )

        return (
            self.conversation_engine
            .session_repository
            .get_session(
                normalized_number
            )
        )

    def cancel_conversation(
        self,
        whatsapp_number,
    ):
        normalized_number = (
            self._validate_authorized_number(
                whatsapp_number
            )
        )

        deleted = (
            self.conversation_engine
            .session_repository
            .delete_session(
                normalized_number
            )
        )

        if not deleted:
            return {
                "cancelled": False,
                "action": "no_active_conversation",
                "message": (
                    "No existe una conversación "
                    "activa para cancelar."
                ),
            }

        return {
            "cancelled": True,
            "action": "conversation_cancelled",
            "message": (
                "La conversación fue cancelada."
            ),
        }

    def _validate_authorized_number(
        self,
        whatsapp_number,
    ):
        normalized_number = (
            self._normalize_number(
                whatsapp_number
            )
        )

        if (
            normalized_number
            != self.allowed_number
        ):
            raise PermissionError(
                "El número de WhatsApp "
                "no está autorizado"
            )

        return normalized_number

    @staticmethod
    def _normalize_number(
        whatsapp_number,
    ):
        if whatsapp_number is None:
            raise ValueError(
                "El número de WhatsApp "
                "es obligatorio"
            )

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