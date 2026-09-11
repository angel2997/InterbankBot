import argparse
import os

from dotenv import load_dotenv

from services.whatsapp_service import (
    WhatsappService,
)


EXIT_COMMANDS = {
    "salir",
    "exit",
}

CANCEL_COMMANDS = {
    "cancelar",
    "cancel",
}


def run_console(
    estado_id,
    whatsapp_number=None,
    whatsapp_service=None,
    input_function=input,
    output_function=print,
):
    load_dotenv()

    configured_number = (
        whatsapp_number
        or os.getenv(
            "WHATSAPP_ALLOWED_NUMBER"
        )
    )

    if not configured_number:
        raise ValueError(
            "No se configuró "
            "WHATSAPP_ALLOWED_NUMBER en .env"
        )

    service = (
        whatsapp_service
        or WhatsappService(
            allowed_number=configured_number
        )
    )

    service.prepare_tables()

    output_function(
        "=" * 60
    )

    output_function(
        "INTERBANKBOT"
    )

    output_function(
        "Simulador de conversación"
    )

    output_function(
        "=" * 60
    )

    output_function(
        'Comandos disponibles: '
        '"Cancelar" y "Salir".'
    )

    output_function("")

    active_session = (
        service.get_active_session(
            configured_number
        )
    )

    if active_session is None:
        result = service.start_conversation(
            whatsapp_number=configured_number,
            estado_id=estado_id,
        )

        output_function(
            result["message"]
        )

        if result["completed"]:
            return result

    else:
        output_function(
            "Se recuperó una conversación "
            "pendiente."
        )

        output_function("")

        result = (
            service.conversation_engine
            .conversation_service
            .build_next_question(
                active_session["estado_id"]
            )
        )

        output_function(
            result["message"]
        )

    while True:
        output_function("")

        user_message = input_function(
            "Tú: "
        )

        normalized_message = str(
            user_message
        ).strip()

        if (
            normalized_message.casefold()
            in EXIT_COMMANDS
        ):
            output_function(
                "Simulador finalizado."
            )

            return {
                "action": "simulator_closed",
                "completed": False,
                "message": (
                    "Simulador finalizado."
                ),
            }

        if (
            normalized_message.casefold()
            in CANCEL_COMMANDS
        ):
            result = (
                service.cancel_conversation(
                    configured_number
                )
            )

            output_function("")
            output_function(
                result["message"]
            )

            return result

        result = service.receive_message(
            whatsapp_number=configured_number,
            message=normalized_message,
        )

        output_function("")
        output_function(
            "InterbankBot:"
        )

        output_function(
            result["message"]
        )

        if result.get(
            "completed",
            False,
        ):
            return result


def build_argument_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Simulador local de conversación "
            "de InterbankBot"
        )
    )

    parser.add_argument(
        "--estado-id",
        type=int,
        required=True,
        help=(
            "Identificador del estado "
            "de cuenta que se procesará"
        ),
    )

    return parser


def main():
    parser = build_argument_parser()

    arguments = parser.parse_args()

    try:
        run_console(
            estado_id=arguments.estado_id
        )

    except (
        ValueError,
        LookupError,
        PermissionError,
    ) as error:
        print(
            f"Error: {error}"
        )


if __name__ == "__main__":
    main()