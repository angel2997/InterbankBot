import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from repositories.estado_repository import (
    EstadoRepository,
)
from repositories.movimiento_asignacion_repository import (
    MovimientoAsignacionRepository,
)


class TxtService:

    def __init__(
        self,
        output_folder=None,
    ):
        project_dir = (
            Path(__file__).resolve().parent.parent
        )

        self.output_folder = (
            Path(output_folder)
            if output_folder is not None
            else project_dir / "txt"
        )

        self.movimiento_repository = (
            MovimientoAsignacionRepository()
        )

        self.estado_repository = (
            EstadoRepository()
        )

    def generate_person_files(
        self,
        estado_id,
    ):
        movements = (
            self.movimiento_repository
            .list_movements_by_statement(
                estado_id
            )
        )

        if not movements:
            raise LookupError(
                "No existen movimientos asignados "
                "para generar archivos TXT"
            )

        statement = (
            self.estado_repository
            .get_statement_summary(
                estado_id
            )
        )

        movements_by_person = (
            self._group_movements_by_person(
                movements
            )
        )

        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        generated_files = []

        for person_name, person_movements in (
            movements_by_person.items()
        ):
            content = (
                self._build_person_content(
                    period=statement["periodo"],
                    person_name=person_name,
                    movements=person_movements,
                )
            )

            safe_file_name = (
                self._build_safe_file_name(
                    person_name
                )
            )

            file_path = (
                self.output_folder
                / f"{safe_file_name}.txt"
            )

            file_path.write_text(
                content,
                encoding="utf-8",
            )

            totals = (
                self._calculate_totals(
                    person_movements
                )
            )

            generated_files.append(
                {
                    "person_name": person_name,
                    "file_name": file_path.name,
                    "file_path": file_path,
                    "movement_count": len(
                        person_movements
                    ),
                    "total_pen_cents": (
                        totals["PEN"]
                    ),
                    "total_usd_cents": (
                        totals["USD"]
                    ),
                }
            )

        return generated_files

    def _build_person_content(
        self,
        period,
        person_name,
        movements,
    ):
        totals = self._calculate_totals(
            movements
        )

        lines = [
            "INTERBANKBOT",
            "DETALLE DE CONSUMOS",
            "",
            f"Periodo: {period or 'No especificado'}",
            f"Persona: {person_name}",
            "",
            "=" * 60,
            "",
        ]

        for movement_number, movement in enumerate(
            movements,
            start=1,
        ):
            currency_symbol = (
                self._get_currency_symbol(
                    movement["moneda"]
                )
            )

            formatted_amount = (
                self._format_money(
                    movement["monto_centimos"],
                    currency_symbol,
                )
            )

            lines.extend(
                [
                    (
                        "Movimiento: "
                        f"{movement_number}"
                    ),
                    (
                        "Fecha: "
                        f"{movement['fecha']}"
                    ),
                    (
                        "Descripción: "
                        f"{movement['descripcion']}"
                    ),
                    (
                        "Moneda: "
                        f"{movement['moneda']}"
                    ),
                    (
                        "Monto: "
                        f"{formatted_amount}"
                    ),
                    "",
                    "-" * 60,
                    "",
                ]
            )

        lines.extend(
            [
                "RESUMEN DE LA PERSONA",
                "",
                (
                    "Total en soles: "
                    f"{self._format_money(
                        totals['PEN'],
                        'S/',
                    )}"
                ),
                (
                    "Total en dólares: "
                    f"{self._format_money(
                        totals['USD'],
                        'US$',
                    )}"
                ),
                "",
            ]
        )

        return "\n".join(
            lines
        )

    @staticmethod
    def _group_movements_by_person(
        movements,
    ):
        grouped = defaultdict(list)

        for movement in movements:
            grouped[
                movement["persona"]
            ].append(
                movement
            )

        return dict(
            sorted(
                grouped.items(),
                key=lambda item: (
                    item[0].casefold()
                ),
            )
        )

    @staticmethod
    def _calculate_totals(
        movements,
    ):
        totals = {
            "PEN": 0,
            "USD": 0,
        }

        for movement in movements:
            currency = movement["moneda"]

            if currency not in totals:
                raise ValueError(
                    "La moneda del movimiento "
                    "no es válida"
                )

            totals[currency] += (
                movement["monto_centimos"]
            )

        return totals

    @staticmethod
    def _format_money(
        amount_cents,
        currency_symbol,
    ):
        amount = (
            Decimal(amount_cents)
            / Decimal("100")
        )

        return (
            f"{currency_symbol} "
            f"{amount:,.2f}"
        )

    @staticmethod
    def _get_currency_symbol(
        currency,
    ):
        if currency == "PEN":
            return "S/"

        if currency == "USD":
            return "US$"

        raise ValueError(
            "La moneda del movimiento "
            "no es válida"
        )

    @staticmethod
    def _build_safe_file_name(
        person_name,
    ):
        normalized_name = " ".join(
            str(person_name).split()
        )

        safe_name = re.sub(
            r'[<>:"/\\|?]',
            "",
            normalized_name,
        )

        safe_name = safe_name.rstrip(
            ". "
        )

        if not safe_name:
            raise ValueError(
                "No se puede generar un nombre "
                "de archivo para la persona"
            )

        return safe_name