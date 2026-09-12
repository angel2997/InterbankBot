import os

import requests
from dotenv import load_dotenv


class WhatsappCloudApiService:

    def __init__(
        self,
        access_token=None,
        phone_number_id=None,
        api_version=None,
        http_client=None,
        timeout_seconds=30,
    ):
        load_dotenv()

        if access_token is None:
            self.access_token = os.getenv(
                "WHATSAPP_ACCESS_TOKEN"
            )
        else:
            self.access_token = access_token

        if phone_number_id is None:
            self.phone_number_id = os.getenv(
                "WHATSAPP_PHONE_NUMBER_ID"
            )
        else:
            self.phone_number_id = (
                phone_number_id
            )

        if api_version is None:
            self.api_version = (
                os.getenv(
                    "WHATSAPP_API_VERSION"
                )
                or "v25.0"
            )
        else:
            self.api_version = api_version

        self.http_client = (
            http_client
            or requests
        )

        self.timeout_seconds = (
            timeout_seconds
        )

        self._validate_configuration()

    def send_text_message(
        self,
        recipient_number,
        message,
    ):
        normalized_number = (
            self._normalize_number(
                recipient_number
            )
        )

        normalized_message = str(
            message
        ).strip()

        if not normalized_message:
            raise ValueError(
                "El mensaje no puede "
                "estar vacío"
            )

        endpoint = self._build_endpoint()

        headers = {
            "Authorization": (
                f"Bearer {self.access_token}"
            ),
            "Content-Type": (
                "application/json"
            ),
        }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": normalized_message,
            },
        }

        try:
            response = self.http_client.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )

        except requests.Timeout as error:
            raise TimeoutError(
                "WhatsApp Cloud API no respondió "
                "dentro del tiempo esperado"
            ) from error

        except requests.RequestException as error:
            raise ConnectionError(
                "No se pudo conectar con "
                "WhatsApp Cloud API"
            ) from error

        if not response.ok:
            raise RuntimeError(
                self._build_safe_error_message(
                    response
                )
            )

        try:
            response_data = response.json()

        except ValueError as error:
            raise ValueError(
                "WhatsApp Cloud API devolvió "
                "una respuesta JSON inválida"
            ) from error

        messages = response_data.get(
            "messages"
        )

        if (
            not isinstance(messages, list)
            or not messages
        ):
            raise ValueError(
                "WhatsApp Cloud API no devolvió "
                "el identificador del mensaje"
            )

        message_id = messages[0].get(
            "id"
        )

        if not message_id:
            raise ValueError(
                "WhatsApp Cloud API devolvió "
                "un mensaje sin identificador"
            )

        return {
            "sent": True,
            "recipient_number": (
                normalized_number
            ),
            "message_id": message_id,
            "status_code": (
                response.status_code
            ),
        }

    def _build_endpoint(self):
        return (
            "https://graph.facebook.com/"
            f"{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

    def _validate_configuration(self):
        missing_variables = []

        if not self.access_token:
            missing_variables.append(
                "WHATSAPP_ACCESS_TOKEN"
            )

        if not self.phone_number_id:
            missing_variables.append(
                "WHATSAPP_PHONE_NUMBER_ID"
            )

        if not self.api_version:
            missing_variables.append(
                "WHATSAPP_API_VERSION"
            )

        if missing_variables:
            missing_text = ", ".join(
                missing_variables
            )

            raise ValueError(
                "Falta configurar: "
                f"{missing_text}"
            )

        if not str(
            self.phone_number_id
        ).isdigit():
            raise ValueError(
                "WHATSAPP_PHONE_NUMBER_ID "
                "debe contener solamente dígitos"
            )

        if not str(
            self.api_version
        ).startswith("v"):
            raise ValueError(
                "WHATSAPP_API_VERSION debe tener "
                "un formato como v25.0"
            )

        if (
            not isinstance(
                self.timeout_seconds,
                int,
            )
            or self.timeout_seconds <= 0
        ):
            raise ValueError(
                "El tiempo de espera debe ser "
                "un entero mayor que cero"
            )

    @staticmethod
    def _normalize_number(
        recipient_number,
    ):
        if recipient_number is None:
            raise ValueError(
                "El número destinatario "
                "es obligatorio"
            )

        normalized_number = "".join(
            str(recipient_number).split()
        )

        normalized_number = (
            normalized_number
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )

        if normalized_number.startswith(
            "+"
        ):
            normalized_number = (
                normalized_number[1:]
            )

        if not normalized_number:
            raise ValueError(
                "El número destinatario "
                "es obligatorio"
            )

        if not normalized_number.isdigit():
            raise ValueError(
                "El número destinatario debe "
                "contener solamente dígitos"
            )

        return normalized_number

    @staticmethod
    def _build_safe_error_message(
        response,
    ):
        detail = (
            "Error desconocido"
        )

        try:
            response_data = response.json()

            error_data = response_data.get(
                "error",
                {},
            )

            detail = error_data.get(
                "message",
                detail,
            )

        except ValueError:
            if response.text:
                detail = response.text[
                    :300
                ]

        return (
            "WhatsApp Cloud API rechazó "
            "la solicitud. "
            f"Código HTTP: {response.status_code}. "
            f"Detalle: {detail}"
        )