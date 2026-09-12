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
from services.conversation_service import (
    ConversationService,
)

from services.txt_service import TxtService


class ConversationEngineService:

    def __init__(
        self,
        conversation_service=None,
        session_repository=None,
        txt_service=None,
    ):
        self.conversation_service = (
            conversation_service
            or ConversationService()
        )

        self.session_repository = (
            session_repository
            or ConversationSessionRepository()
        )

        self.txt_service = (
            txt_service
            or TxtService()
        )

    def start_conversation(
        self,
        whatsapp_number,
        estado_id,
    ):
        question = (
            self.conversation_service
            .build_next_question(
                estado_id
            )
        )

        if question["completed"]:
            self.session_repository.delete_session(
                whatsapp_number
            )

            return {
                "action": "completed",
                "completed": True,
                "message": question["message"],
            }

        consumption_id = (
            question["consumption"]["id"]
        )

        session = (
            self.session_repository
            .save_session(
                whatsapp_number=whatsapp_number,
                estado_id=estado_id,
                conversation_state=(
                    WAITING_PERSON
                ),
                consumption_id=consumption_id,
                person_id=None,
                person_name=None,
                options=question["options"],
            )
        )

        return {
            "action": "waiting_person",
            "completed": False,
            "message": question["message"],
            "session": session,
            "consumption": (
                question["consumption"]
            ),
        }

    def process_message(
        self,
        whatsapp_number,
        message,
    ):
        session = (
            self.session_repository
            .get_session(
                whatsapp_number
            )
        )

        if session is None:
            raise LookupError(
                "No existe una conversación "
                "activa para este número"
            )

        conversation_state = (
            session["estado_conversacion"]
        )

        if conversation_state == WAITING_PERSON:
            return self._process_person_message(
                whatsapp_number=whatsapp_number,
                message=message,
                session=session,
            )

        if (
            conversation_state
            == WAITING_NEW_PERSON_NAME
        ):
            return (
                self._process_new_person_name(
                    whatsapp_number=whatsapp_number,
                    message=message,
                    session=session,
                )
            )

        if conversation_state == WAITING_AMOUNT:
            return self._process_amount_message(
                whatsapp_number=whatsapp_number,
                message=message,
                session=session,
            )

        raise ValueError(
            "El estado de la conversación "
            "no es válido"
        )

    def _process_person_message(
        self,
        whatsapp_number,
        message,
        session,
    ):
        normalized_message = str(
            message
        ).strip()

        if (
            normalized_message.casefold()
            == "deshacer"
        ):
            return self._process_undo(
                whatsapp_number=whatsapp_number,
                session=session,
            )

        selection = (
            self.conversation_service
            .process_person_selection(
                estado_id=session["estado_id"],
                consumption_id=(
                    session["consumo_id"]
                ),
                selected_option=(
                    normalized_message
                ),
                options=session["opciones"],
            )
        )

        if not selection["valid"]:
            return {
                "action": "invalid_option",
                "completed": False,
                "message": selection["message"],
                "session": session,
            }

        if (
            selection["action"]
            == "request_new_person_name"
        ):
            updated_session = (
                self.session_repository
                .update_conversation_state(
                    whatsapp_number=(
                        whatsapp_number
                    ),
                    conversation_state=(
                        WAITING_NEW_PERSON_NAME
                    ),
                    consumption_id=(
                        session["consumo_id"]
                    ),
                    person_id=None,
                    person_name=None,
                    options={},
                )
            )

            return {
                "action": (
                    "waiting_new_person_name"
                ),
                "completed": False,
                "message": selection["message"],
                "session": updated_session,
            }

        updated_session = (
            self.session_repository
            .update_conversation_state(
                whatsapp_number=whatsapp_number,
                conversation_state=(
                    WAITING_AMOUNT
                ),
                consumption_id=(
                    session["consumo_id"]
                ),
                person_id=selection["person_id"],
                person_name=(
                    selection["person_name"]
                ),
                options={},
            )
        )

        return {
            "action": "waiting_amount",
            "completed": False,
            "message": selection["message"],
            "session": updated_session,
        }

    def _process_new_person_name(
        self,
        whatsapp_number,
        message,
        session,
    ):
        result = (
            self.conversation_service
            .create_temporary_person(
                estado_id=session["estado_id"],
                consumption_id=(
                    session["consumo_id"]
                ),
                person_name=message,
            )
        )

        if not result["created"]:
            return {
                "action": result["action"],
                "completed": False,
                "message": result["message"],
                "session": session,
            }

        updated_session = (
            self.session_repository
            .update_conversation_state(
                whatsapp_number=whatsapp_number,
                conversation_state=(
                    WAITING_AMOUNT
                ),
                consumption_id=(
                    session["consumo_id"]
                ),
                person_id=result["person_id"],
                person_name=(
                    result["person_name"]
                ),
                options={},
            )
        )

        return {
            "action": "waiting_amount",
            "completed": False,
            "message": result["message"],
            "session": updated_session,
        }

    def _process_amount_message(
        self,
        whatsapp_number,
        message,
        session,
    ):
        try:
            assignment = (
                self.conversation_service
                .register_assignment(
                    consumption_id=(
                        session["consumo_id"]
                    ),
                    person_id=(
                        session["persona_id"]
                    ),
                    user_input=message,
                )
            )

        except ValueError as error:
            return {
                "action": "invalid_amount",
                "completed": False,
                "message": str(error),
                "session": session,
            }

        next_question = (
            self.conversation_service
            .build_next_question(
                session["estado_id"]
            )
        )

        if next_question["completed"]:
            try:
                txt_result = (
                    self.txt_service
                    .generate_all_files(
                        estado_id=(
                            session["estado_id"]
                        )
                    )
                )

            except (
                ValueError,
                LookupError,
                OSError,
            ) as error:
                return {
                    "action": (
                        "txt_generation_failed"
                    ),
                    "completed": False,
                    "message": (
                        f"{assignment['message']}\n\n"
                        "Todos los consumos fueron "
                        "asignados, pero no se pudieron "
                        "generar los archivos TXT.\n\n"
                        f"Detalle: {error}\n\n"
                        "La sesión se conservará para "
                        "poder reintentar."
                    ),
                    "assignment": assignment,
                    "txt_result": None,
                    "session": session,
                }

            self.session_repository.delete_session(
                whatsapp_number
            )

            person_file_count = (
                txt_result[
                    "person_file_count"
                ]
            )

            generated_file_count = (
                txt_result[
                    "generated_file_count"
                ]
            )

            if txt_result["balanced"]:
                verification_message = (
                    "La comprobación de Total.txt "
                    "no presenta diferencias."
                )

            else:
                verification_message = (
                    "Advertencia: Total.txt presenta "
                    "una diferencia pendiente "
                    "de revisión."
                )

            message_text = (
                f"{assignment['message']}\n\n"
                f"{next_question['message']}\n\n"
                "Archivos TXT generados "
                "correctamente.\n"
                "Archivos individuales: "
                f"{person_file_count}\n"
                "Archivo consolidado: Total.txt\n"
                "Total de archivos: "
                f"{generated_file_count}\n\n"
                f"{verification_message}"
            )

            return {
                "action": "completed",
                "completed": True,
                "message": message_text,
                "assignment": assignment,
                "txt_result": txt_result,
                "session": None,
            }

        updated_session = (
            self.session_repository
            .update_conversation_state(
                whatsapp_number=whatsapp_number,
                conversation_state=(
                    WAITING_PERSON
                ),
                consumption_id=(
                    next_question[
                        "consumption"
                    ]["id"]
                ),
                person_id=None,
                person_name=None,
                options=next_question["options"],
            )
        )

        message_text = (
            f"{assignment['message']}\n\n"
            f"{next_question['message']}"
        )

        return {
            "action": "waiting_person",
            "completed": False,
            "message": message_text,
            "assignment": assignment,
            "session": updated_session,
        }

    def _process_undo(
        self,
        whatsapp_number,
        session,
    ):
        try:
            undo_result = (
                self.conversation_service
                .undo_last_assignment(
                    consumption_id=(
                        session["consumo_id"]
                    )
                )
            )

        except LookupError as error:
            return {
                "action": "nothing_to_undo",
                "completed": False,
                "message": str(error),
                "session": session,
            }

        question = (
            self.conversation_service
            .build_next_question(
                session["estado_id"]
            )
        )

        updated_session = (
            self.session_repository
            .update_conversation_state(
                whatsapp_number=whatsapp_number,
                conversation_state=(
                    WAITING_PERSON
                ),
                consumption_id=(
                    question["consumption"]["id"]
                ),
                person_id=None,
                person_name=None,
                options=question["options"],
            )
        )

        message_text = (
            f"{undo_result['message']}\n\n"
            f"{question['message']}"
        )

        return {
            "action": "assignment_undone",
            "completed": False,
            "message": message_text,
            "undo": undo_result,
            "session": updated_session,
        }