import hashlib
from datetime import datetime
from pathlib import Path

from database.db import get_connection


class EstadoRepository:

    def create_table(self):
        with get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS estados_procesados (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo TEXT,
                    hash_archivo TEXT NOT NULL UNIQUE,
                    nombre_pdf TEXT NOT NULL,
                    fecha_correo TEXT,
                    fecha_procesado TEXT NOT NULL,
                    estado TEXT NOT NULL
                )
                """
            )

    def calculate_hash(self, pdf_path):
        pdf_path = Path(pdf_path)
        sha256 = hashlib.sha256()

        with pdf_path.open("rb") as file:
            for block in iter(
                lambda: file.read(65536),
                b"",
            ):
                sha256.update(block)

        return sha256.hexdigest()

    def is_processed(self, pdf_path):
        file_hash = self.calculate_hash(pdf_path)

        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT id
                FROM estados_procesados
                WHERE hash_archivo = ?
                """,
                (file_hash,),
            ).fetchone()

        return row is not None

    def register(
        self,
        pdf_path,
        email_date=None,
        period=None,
        status="DESCARGADO",
    ):
        pdf_path = Path(pdf_path)
        file_hash = self.calculate_hash(pdf_path)

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO estados_procesados (
                    periodo,
                    hash_archivo,
                    nombre_pdf,
                    fecha_correo,
                    fecha_procesado,
                    estado
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    period,
                    file_hash,
                    pdf_path.name,
                    email_date,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                    status,
                ),
            )

        return cursor.rowcount == 1