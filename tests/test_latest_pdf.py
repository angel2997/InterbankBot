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

print("=" * 60)
print("ÚLTIMO CORREO CON PDF")
print("=" * 60)
print("Asunto:", message.get("subject"))
print("Fecha:", message.get("receivedDateTime"))
print("Archivo:", attachment.get("name"))
print("Tipo:", attachment.get("contentType"))
print("Tamaño:", attachment.get("size"), "bytes")