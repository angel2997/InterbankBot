import unittest
from unittest.mock import MagicMock

import requests

from services.whatsapp_cloud_api_service import (
    WhatsappCloudApiService,
)


class WhatsappCloudApiServiceTest(
    unittest.TestCase
):

    def setUp(self):
        self.http_client = MagicMock()

        self.response = MagicMock()
        self.response.ok = True
        self.response.status_code = 200
        self.response.json.return_value = {
            "messaging_product": "whatsapp",
            "contacts": [
                {
                    "input": "51999999999",
                    "wa_id": "51999999999",
                },
            ],
            "messages": [
                {
                    "id": "wamid.test-message",
                },
            ],
        }

        self.http_client.post.return_value = (
            self.response
        )

        self.service = (
            WhatsappCloudApiService(
                access_token="test-token",
                phone_number_id=(
                    "1277332822134155"
                ),
                api_version="v25.0",
                http_client=self.http_client,
                timeout_seconds=20,
            )
        )

    def test_builds_correct_endpoint(
        self,
    ):
        endpoint = (
            self.service
            ._build_endpoint()
        )

        self.assertEqual(
            (
                "https://graph.facebook.com/"
                "v25.0/"
                "1277332822134155/messages"
            ),
            endpoint,
        )

    def test_sends_text_message(
        self,
    ):
        result = (
            self.service
            .send_text_message(
                recipient_number=(
                    "+51 999 999 999"
                ),
                message=(
                    "Hola desde InterbankBot"
                ),
            )
        )

        self.assertTrue(
            result["sent"]
        )

        self.assertEqual(
            "51999999999",
            result["recipient_number"],
        )

        self.assertEqual(
            "wamid.test-message",
            result["message_id"],
        )

        self.assertEqual(
            200,
            result["status_code"],
        )

    def test_sends_expected_payload(
        self,
    ):
        self.service.send_text_message(
            recipient_number=(
                "+51 999 999 999"
            ),
            message="Mensaje de prueba",
        )

        self.http_client.post.assert_called_once()

        call = (
            self.http_client
            .post
            .call_args
        )

        self.assertEqual(
            {
                "messaging_product": (
                    "whatsapp"
                ),
                "recipient_type": (
                    "individual"
                ),
                "to": "51999999999",
                "type": "text",
                "text": {
                    "preview_url": False,
                    "body": (
                        "Mensaje de prueba"
                    ),
                },
            },
            call.kwargs["json"],
        )

        self.assertEqual(
            20,
            call.kwargs["timeout"],
        )

    def test_sends_bearer_header(
        self,
    ):
        self.service.send_text_message(
            recipient_number=(
                "51999999999"
            ),
            message="Hola",
        )

        headers = (
            self.http_client
            .post
            .call_args
            .kwargs["headers"]
        )

        self.assertEqual(
            "Bearer test-token",
            headers["Authorization"],
        )

        self.assertEqual(
            "application/json",
            headers["Content-Type"],
        )

    def test_normalizes_number(
        self,
    ):
        numbers = (
            "+51 999 999 999",
            "51 999 999 999",
            "+51-999-999-999",
            "+51 (999) 999 999",
        )

        for number in numbers:
            with self.subTest(
                number=number
            ):
                normalized = (
                    self.service
                    ._normalize_number(
                        number
                    )
                )

                self.assertEqual(
                    "51999999999",
                    normalized,
                )

    def test_rejects_empty_message(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "no puede estar vacío",
        ):
            self.service.send_text_message(
                recipient_number=(
                    "51999999999"
                ),
                message="   ",
            )

        self.http_client.post.assert_not_called()

    def test_rejects_invalid_number(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "solamente dígitos",
        ):
            self.service.send_text_message(
                recipient_number=(
                    "numero-invalido"
                ),
                message="Hola",
            )

    def test_rejects_missing_configuration(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "WHATSAPP_ACCESS_TOKEN",
        ):
            WhatsappCloudApiService(
                access_token="",
                phone_number_id="123456",
                api_version="v25.0",
                http_client=self.http_client,
            )

    def test_handles_http_error(
        self,
    ):
        self.response.ok = False
        self.response.status_code = 400
        self.response.json.return_value = {
            "error": {
                "message": (
                    "Invalid parameter"
                ),
            },
        }

        with self.assertRaisesRegex(
            RuntimeError,
            "Código HTTP: 400",
        ):
            self.service.send_text_message(
                recipient_number=(
                    "51999999999"
                ),
                message="Hola",
            )

    def test_handles_invalid_json(
        self,
    ):
        self.response.json.side_effect = (
            ValueError()
        )

        with self.assertRaisesRegex(
            ValueError,
            "JSON inválida",
        ):
            self.service.send_text_message(
                recipient_number=(
                    "51999999999"
                ),
                message="Hola",
            )

    def test_handles_timeout(
        self,
    ):
        self.http_client.post.side_effect = (
            requests.Timeout()
        )

        with self.assertRaisesRegex(
            TimeoutError,
            "tiempo esperado",
        ):
            self.service.send_text_message(
                recipient_number=(
                    "51999999999"
                ),
                message="Hola",
            )

    def test_result_does_not_expose_token(
        self,
    ):
        result = (
            self.service
            .send_text_message(
                recipient_number=(
                    "51999999999"
                ),
                message="Hola",
            )
        )

        self.assertNotIn(
            "test-token",
            str(result),
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )