import sqlite3

conn = sqlite3.connect("../database/interbank.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS estados_procesados(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo TEXT NOT NULL,
    hash_archivo TEXT NOT NULL,
    nombre_pdf TEXT,
    fecha_correo TEXT,
    fecha_procesado TEXT,
    estado TEXT
)
""")

conn.commit()
conn.close()

print("Base creada correctamente")