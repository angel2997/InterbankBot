from pathlib import Path

from services.pdf_service import PdfService


PROJECT_DIR = Path(__file__).resolve().parent.parent
PDF_FOLDER = PROJECT_DIR / "pdf"

pdf_files = list(PDF_FOLDER.glob("*.pdf"))

if not pdf_files:
    raise FileNotFoundError(
        "No hay archivos PDF en la carpeta pdf"
    )

latest_pdf = max(
    pdf_files,
    key=lambda file: file.stat().st_mtime,
)

pdf_service = PdfService()
result = pdf_service.extract_text(latest_pdf)

print("=" * 60)
print("PDF ABIERTO CORRECTAMENTE")
print("=" * 60)
print("Archivo:", latest_pdf.name)
print("Páginas:", result["page_count"])
print(
    "Caracteres extraídos:",
    len(result["text"]),
)
print()
print("Vista previa:")
print(result["text"])