import unittest
from decimal import Decimal

from services.conversation_service import (
    ConversationService,
)


class AssignmentAmountTest(
    unittest.TestCase
):

    def setUp(self):
        self.service = ConversationService()

    def test_accepts_valid_fixed_amount_formats(
        self,
    ):
        cases = {
            "50": 5000,
            "50.5": 5050,
            "50.50": 5050,
            "S/ 50": 5000,
            "S/50.50": 5050,
        }

        for user_input, expected_cents in (
            cases.items()
        ):
            with self.subTest(
                user_input=user_input
            ):
                result = (
                    self.service
                    .calculate_assignment_amount(
                        user_input=user_input,
                        pending_cents=10000,
                    )
                )

                self.assertEqual(
                    "amount",
                    result["input_type"],
                )
                self.assertEqual(
                    expected_cents,
                    result["amount_cents"],
                )

    def test_percentage_uses_pending_balance(
        self,
    ):
        result = (
            self.service
            .calculate_assignment_amount(
                user_input="50%",
                pending_cents=6000,
            )
        )

        self.assertEqual(
            "percentage",
            result["input_type"],
        )
        self.assertEqual(
            Decimal("50"),
            result["input_value"],
        )
        self.assertEqual(
            3000,
            result["amount_cents"],
        )

    def test_accepts_decimal_percentage(
        self,
    ):
        result = (
            self.service
            .calculate_assignment_amount(
                user_input="33.33%",
                pending_cents=10000,
            )
        )

        self.assertEqual(
            "percentage",
            result["input_type"],
        )
        self.assertEqual(
            Decimal("33.33"),
            result["input_value"],
        )
        self.assertEqual(
            3333,
            result["amount_cents"],
        )

    def test_percentage_rounds_half_up(
        self,
    ):
        result = (
            self.service
            .calculate_assignment_amount(
                user_input="50%",
                pending_cents=101,
            )
        )

        self.assertEqual(
            51,
            result["amount_cents"],
        )

    def test_todo_assigns_entire_balance(
        self,
    ):
        result = (
            self.service
            .calculate_assignment_amount(
                user_input="Todo",
                pending_cents=3575,
            )
        )

        self.assertEqual(
            "balance",
            result["input_type"],
        )
        self.assertEqual(
            3575,
            result["amount_cents"],
        )

    def test_saldo_assigns_entire_balance(
        self,
    ):
        result = (
            self.service
            .calculate_assignment_amount(
                user_input="Saldo",
                pending_cents=3575,
            )
        )

        self.assertEqual(
            "balance",
            result["input_type"],
        )
        self.assertEqual(
            3575,
            result["amount_cents"],
        )

    def test_commands_ignore_uppercase(
        self,
    ):
        commands = (
            "todo",
            "TODO",
            "Todo",
            "saldo",
            "SALDO",
            "Saldo",
        )

        for command in commands:
            with self.subTest(
                command=command
            ):
                result = (
                    self.service
                    .calculate_assignment_amount(
                        user_input=command,
                        pending_cents=2500,
                    )
                )

                self.assertEqual(
                    2500,
                    result["amount_cents"],
                )

    def test_rejects_invalid_inputs(
        self,
    ):
        invalid_values = (
            "",
            "0",
            "-10",
            "0%",
            "101%",
            "abc",
            "50%%",
            "S/ veinte",
            "10.999",
        )

        for user_input in invalid_values:
            with self.subTest(
                user_input=user_input
            ):
                with self.assertRaises(
                    ValueError
                ):
                    (
                        self.service
                        .calculate_assignment_amount(
                            user_input=user_input,
                            pending_cents=10000,
                        )
                    )

    def test_rejects_amount_above_balance(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "superar el saldo pendiente",
        ):
            (
                self.service
                .calculate_assignment_amount(
                    user_input="60",
                    pending_cents=5000,
                )
            )

    def test_question_displays_balance(
        self,
    ):
        message = (
            self.service
            .build_assignment_amount_question(
                person_name="Flor",
                pending_cents=6050,
                currency_symbol="S/",
            )
        )

        self.assertIn(
            "¿Cuánto deseas asignar a Flor?",
            message,
        )
        self.assertIn(
            "Saldo pendiente: S/ 60.50",
            message,
        )
        self.assertIn(
            "porcentaje del saldo pendiente",
            message,
        )
        self.assertIn(
            "Todo o Saldo",
            message,
        )


if __name__ == "__main__":
    unittest.main(
        verbosity=2
    )