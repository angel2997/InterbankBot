from services.auth_service import AuthService
from services.mail_service import MailService


FOLDER_NAME = "Estado Cuenta Interbank"


auth_service = AuthService()
token = auth_service.login()

mail_service = MailService(
    access_token=token["access_token"]
)

folder = mail_service.find_folder_by_name(
    FOLDER_NAME
)

result = mail_service.find_latest_message_with_pdf(
    folder["id"]
)

message = result["message"]
attachment = result["attachment"]

pdf_path = mail_service.download_attachment(
    message_id=message["id"],
    attachment=attachment,
)

print("=" * 60)
print("PDF DESCARGADO")
print("=" * 60)
print("Archivo:", pdf_path.name)
print("Ubicación:", pdf_path.parent)
print("Tamaño:", pdf_path.stat().st_size, "bytes")
print("Existe:", pdf_path.exists())