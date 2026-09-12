import os

from dotenv import load_dotenv

from services.whatsapp_cloud_api_service import (
    WhatsappCloudApiService,
)


def main():
    load_dotenv()

    recipient_number = os.getenv(
        "WHATSAPP_ALLOWED_NUMBER"
    )

    if not recipient_number:
        raise ValueError(
            "Falta configurar "
            "WHATSAPP_ALLOWED_NUMBER "
            "en el archivo .env"
        )

    whatsapp_service = (
        WhatsappCloudApiService()
    )

    message = (
        "Hola desde InterbankBot. "
        "La conexión con WhatsApp Cloud API "
        "funciona correctamente."
    )

    print("=" * 60)
    print("PRUEBA REAL DE WHATSAPP CLOUD API")
    print("=" * 60)
    print("Enviando mensaje...")
    print()

    result = (
        whatsapp_service
        .send_text_message(
            recipient_number=(
                recipient_number
            ),
            message=message,
        )
    )

    print("Mensaje enviado correctamente.")
    print(
        "Destinatario:",
        result["recipient_number"],
    )
    print(
        "Identificador del mensaje:",
        result["message_id"],
    )
    print(
        "Código HTTP:",
        result["status_code"],
    )
    print("=" * 60)


if __name__ == "__main__":
    main()