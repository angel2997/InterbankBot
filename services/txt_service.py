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

    def _build_total_content(
        self,
        period,
        payment_pen_cents,
        payment_usd_cents,
        distributed_pen_cents,
        distributed_usd_cents,
        insurance_pen_cents,
        insurance_usd_cents,
        difference_pen_cents,
        difference_usd_cents,
        movements_by_person,
    ):
        balanced = (
            difference_pen_cents == 0
            and difference_usd_cents == 0
        )

        payment_pen = self._format_money(
            payment_pen_cents,
            "S/",
        )

        payment_usd = self._format_money(
            payment_usd_cents,
            "US$",
        )

        distributed_pen = self._format_money(
            distributed_pen_cents,
            "S/",
        )

        distributed_usd = self._format_money(
            distributed_usd_cents,
            "US$",
        )

        insurance_pen = self._format_money(
            insurance_pen_cents,
            "S/",
        )

        insurance_usd = self._format_money(
            insurance_usd_cents,
            "US$",
        )

        difference_pen = self._format_money(
            difference_pen_cents,
            "S/",
        )

        difference_usd = self._format_money(
            difference_usd_cents,
            "US$",
        )

        lines = [
            "INTERBANKBOT",
            (
                "RESUMEN GENERAL DEL "
                "ESTADO DE CUENTA"
            ),
            "",
            (
                "Periodo: "
                f"{period or 'No especificado'}"
            ),
            "",
            "=" * 60,
            "PAGO DEL MES SEGÚN PDF",
            "=" * 60,
            "",
            f"Soles: {payment_pen}",
            f"Dólares: {payment_usd}",
            "",
            "=" * 60,
            (
                "TOTAL DISTRIBUIDO "
                "ENTRE PERSONAS"
            ),
            "=" * 60,
            "",
            f"Soles: {distributed_pen}",
            f"Dólares: {distributed_usd}",
            "",
            "=" * 60,
            "SEGURO DE DESGRAVAMEN",
            "=" * 60,
            "",
            f"Soles: {insurance_pen}",
            f"Dólares: {insurance_usd}",
            "",
            "=" * 60,
            "DIFERENCIA DE COMPROBACIÓN",
            "=" * 60,
            "",
            f"Soles: {difference_pen}",
            f"Dólares: {difference_usd}",
            "",
        ]

        if balanced:
            lines.extend(
                [
                    (
                        "COMPROBACIÓN CORRECTA: "
                        "no existen diferencias."
                    ),
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    (
                        "ADVERTENCIA: existe una "
                        "diferencia pendiente "
                        "de revisión."
                    ),
                    "",
                    (
                        "Verifica que todos los "
                        "consumos hayan sido "
                        "distribuidos correctamente."
                    ),
                    "",
                ]
            )

        lines.extend(
            [
                "=" * 60,
                (
                    "DETALLE DE CUENTAS "
                    "POR PERSONA"
                ),
                "=" * 60,
                "",
            ]
        )

        for person_name, movements in (
            movements_by_person.items()
        ):
            totals = self._calculate_totals(
                movements
            )

            lines.extend(
                [
                    f"PERSONA: {person_name}",
                    "",
                ]
            )

            for movement_number, movement in (
                enumerate(
                    movements,
                    start=1,
                )
            ):
                currency_symbol = (
                    self._get_currency_symbol(
                        movement["moneda"]
                    )
                )

                formatted_amount = (
                    self._format_money(
                        movement[
                            "monto_centimos"
                        ],
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
                    ]
                )

            person_total_pen = (
                self._format_money(
                    totals["PEN"],
                    "S/",
                )
            )

            person_total_usd = (
                self._format_money(
                    totals["USD"],
                    "US$",
                )
            )

            lines.extend(
                [
                    (
                        "Subtotal en soles: "
                        f"{person_total_pen}"
                    ),
                    (
                        "Subtotal en dólares: "
                        f"{person_total_usd}"
                    ),
                    "",
                    "-" * 60,
                    "",
                ]
            )

        lines.extend(
            [
                "=" * 60,
                "FIN DEL REPORTE",
                "=" * 60,
                "",
            ]
        )

        return "\n".join(
            lines
        )

    @staticmethod
    def _validate_statement_summary(
        statement,
    ):
        if statement is None:
            raise ValueError(
                "No se encontró el resumen "
                "del estado de cuenta"
            )

        if not isinstance(
            statement,
            dict,
        ):
            raise TypeError(
                "El resumen del estado de cuenta "
                "debe ser un diccionario"
            )

        required_fields = (
            "pago_mes_soles_centimos",
            "pago_mes_dolares_centimos",
            (
                "seguro_desgravamen_"
                "soles_centimos"
            ),
            (
                "seguro_desgravamen_"
                "dolares_centimos"
            ),
        )

        missing_fields = []

        for field in required_fields:
            if (
                field not in statement
                or statement[field] is None
            ):
                missing_fields.append(
                    field
                )

        if missing_fields:
            missing_fields_text = ", ".join(
                missing_fields
            )

            raise ValueError(
                "El estado de cuenta no tiene "
                "guardado el pago del mes o "
                "el seguro de desgravamen. "
                "Campos pendientes: "
                f"{missing_fields_text}"
            )

        for field in required_fields:
            value = statement[field]

            if isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    "Los importes del resumen "
                    "no pueden ser valores "
                    "booleanos"
                )

            if not isinstance(
                value,
                int,
            ):
                raise TypeError(
                    "Los importes del resumen "
                    "deben estar almacenados "
                    "como números enteros"
                )

            if value < 0:
                raise ValueError(
                    "Los importes del resumen "
                    "no pueden ser negativos"
                )

        return True

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

    def generate_total_file(
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
                    "para generar Total.txt"
                )
    
            statement = (
                self.estado_repository
                .get_statement_summary(
                    estado_id
                )
            )
    
            self._validate_statement_summary(
                statement
            )
    
            distributed_totals = (
                self.movimiento_repository
                .get_distributed_totals(
                    estado_id
                )
            )
    
            payment_pen_cents = (
                statement[
                    "pago_mes_soles_centimos"
                ]
            )
    
            payment_usd_cents = (
                statement[
                    "pago_mes_dolares_centimos"
                ]
            )
    
            insurance_pen_cents = (
                statement[
                    "seguro_desgravamen_"
                    "soles_centimos"
                ]
            )
    
            insurance_usd_cents = (
                statement[
                    "seguro_desgravamen_"
                    "dolares_centimos"
                ]
            )
    
            distributed_pen_cents = (
                distributed_totals["PEN"]
            )
    
            distributed_usd_cents = (
                distributed_totals["USD"]
            )
    
            difference_pen_cents = (
                payment_pen_cents
                - distributed_pen_cents
                - insurance_pen_cents
            )
    
            difference_usd_cents = (
                payment_usd_cents
                - distributed_usd_cents
                - insurance_usd_cents
            )
    
            movements_by_person = (
                self._group_movements_by_person(
                    movements
                )
            )
    
            content = (
                self._build_total_content(
                    period=statement["periodo"],
                    payment_pen_cents=(
                        payment_pen_cents
                    ),
                    payment_usd_cents=(
                        payment_usd_cents
                    ),
                    distributed_pen_cents=(
                        distributed_pen_cents
                    ),
                    distributed_usd_cents=(
                        distributed_usd_cents
                    ),
                    insurance_pen_cents=(
                        insurance_pen_cents
                    ),
                    insurance_usd_cents=(
                        insurance_usd_cents
                    ),
                    difference_pen_cents=(
                        difference_pen_cents
                    ),
                    difference_usd_cents=(
                        difference_usd_cents
                    ),
                    movements_by_person=(
                        movements_by_person
                    ),
                )
            )
    
            self.output_folder.mkdir(
                parents=True,
                exist_ok=True,
            )
    
            file_path = (
                self.output_folder
                / "Total.txt"
            )
    
            file_path.write_text(
                content,
                encoding="utf-8",
            )
    
            return {
                "file_name": file_path.name,
                "file_path": file_path,
                "person_count": len(
                    movements_by_person
                ),
                "movement_count": len(
                    movements
                ),
                "payment_pen_cents": (
                    payment_pen_cents
                ),
                "payment_usd_cents": (
                    payment_usd_cents
                ),
                "distributed_pen_cents": (
                    distributed_pen_cents
                ),
                "distributed_usd_cents": (
                    distributed_usd_cents
                ),
                "insurance_pen_cents": (
                    insurance_pen_cents
                ),
                "insurance_usd_cents": (
                    insurance_usd_cents
                ),
                "difference_pen_cents": (
                    difference_pen_cents
                ),
                "difference_usd_cents": (
                    difference_usd_cents
                ),
                "balanced": (
                    difference_pen_cents == 0
                    and difference_usd_cents == 0
                ),
            }

    def generate_all_files(
        self,
        estado_id,
    ):
        person_files = (
            self.generate_person_files(
                estado_id=estado_id
            )
        )

        total_file = (
            self.generate_total_file(
                estado_id=estado_id
            )
        )

        generated_paths = [
            item["file_path"]
            for item in person_files
        ]

        generated_paths.append(
            total_file["file_path"]
        )

        return {
            "estado_id": estado_id,
            "person_files": person_files,
            "total_file": total_file,
            "person_file_count": len(
                person_files
            ),
            "total_file_count": 1,
            "generated_file_count": len(
                generated_paths
            ),
            "generated_paths": (
                generated_paths
            ),
            "balanced": (
                total_file["balanced"]
            ),
        }

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