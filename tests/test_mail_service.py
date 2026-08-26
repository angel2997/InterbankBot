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

print("=" * 60)
print("CARPETA ENCONTRADA")
print("=" * 60)
print("Nombre:", folder["displayName"])
print("Correos:", folder["totalItemCount"])
print("Subcarpetas:", folder["childFolderCount"])
print("ID encontrado correctamente:", bool(folder["id"]))