import requests
import re
from pathlib import Path


GRAPH_URL = "https://graph.microsoft.com/v1.0"


class MailService:

    def __init__(self, access_token):
        if not access_token:
            raise ValueError(
                "El access_token es obligatorio"
            )

        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def find_folder_by_name(self, folder_name):
        """
        Busca una carpeta raíz por su nombre.

        Devuelve el diccionario de la carpeta encontrada.
        """

        url = f"{GRAPH_URL}/me/mailFolders"

        params = {
            "$select": (
                "id,displayName,parentFolderId,"
                "childFolderCount,totalItemCount"
            ),
            "$top": 100,
        }

        while url:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            for folder in data.get("value", []):
                current_name = folder.get(
                    "displayName",
                    "",
                ).strip()

                if (
                    current_name.casefold()
                    == folder_name.strip().casefold()
                ):
                    return folder

            url = data.get("@odata.nextLink")
            params = None

        raise LookupError(
            f"No se encontró la carpeta: {folder_name}"
        )

    def find_latest_message_with_pdf(
        self,
        folder_id,
    ):
        """
        Busca el correo más reciente que tenga
        un PDF adjunto.
        """

        url = (
            f"{GRAPH_URL}/me/mailFolders/"
            f"{folder_id}/messages"
        )

        params = {
            "$select": (
                "id,subject,receivedDateTime,"
                "hasAttachments,from"
            ),
            "$orderby": "receivedDateTime desc",
            "$top": 25,
        }

        while url:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            for message in data.get("value", []):
                if not message.get("hasAttachments"):
                    continue

                pdf_attachment = (
                    self._find_pdf_attachment(
                        message["id"]
                    )
                )

                if pdf_attachment:
                    return {
                        "message": message,
                        "attachment": pdf_attachment,
                    }

            url = data.get("@odata.nextLink")
            params = None

        raise LookupError(
            "No se encontró ningún correo "
            "con PDF adjunto"
        )

    def _find_pdf_attachment(
        self,
        message_id,
    ):
        """Busca un PDF adjunto dentro de un correo."""

        url = (
            f"{GRAPH_URL}/me/messages/"
            f"{message_id}/attachments"
        )

        params = {
            "$select": (
                "id,name,contentType,size,isInline"
            )
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        attachments = response.json().get(
            "value",
            [],
        )

        for attachment in attachments:
            name = attachment.get(
                "name",
                "",
            )

            content_type = attachment.get(
                "contentType",
                "",
            )

            is_pdf = (
                name.lower().endswith(".pdf")
                or content_type.lower()
                == "application/pdf"
            )

            is_inline = attachment.get(
                "isInline",
                False,
            )

            if is_pdf and not is_inline:
                return attachment

        return None
    
    def download_attachment(
        self,
        message_id,
        attachment,
        destination_folder="pdf",
    ):
        """Descarga un archivo adjunto y devuelve su ruta."""

        attachment_id = attachment.get("id")
        original_name = attachment.get(
            "name",
            "estado_cuenta.pdf",
        )

        if not attachment_id:
            raise ValueError(
                "El adjunto no contiene un ID"
            )

        safe_name = re.sub(
            r"[^A-Za-z0-9._-]",
            "_",
            original_name,
        )

        project_dir = Path(__file__).resolve().parent.parent
        destination = project_dir / destination_folder
        destination.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = destination / safe_name

        url = (
            f"{GRAPH_URL}/me/messages/"
            f"{message_id}/attachments/"
            f"{attachment_id}/$value"
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=60,
        )

        response.raise_for_status()

        if not response.content.startswith(b"%PDF"):
            raise ValueError(
                "El archivo descargado no parece ser un PDF válido"
            )

        file_path.write_bytes(response.content)

        downloaded_size = file_path.stat().st_size

        if downloaded_size == 0:
            file_path.unlink(missing_ok=True)

            raise ValueError(
                "El archivo descargado está vacío"
            )

        return file_path