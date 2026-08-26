import os
from pathlib import Path

from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
AUTHORITY = "https://login.microsoftonline.com/consumers"

SCOPES = [
    "User.Read",
    "Mail.Read",
]

CACHE_PATH = BASE_DIR / "data" / "msal_cache.bin"


class AuthService:

    def __init__(self):
        if not CLIENT_ID:
            raise ValueError(
                "Falta OUTLOOK_CLIENT_ID en el archivo .env"
            )

        CACHE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cache = SerializableTokenCache()
        self._load_cache()

        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=AUTHORITY,
            token_cache=self.cache,
        )

    def _load_cache(self):
        """Carga la sesión anterior si existe."""

        if CACHE_PATH.exists():
            cache_content = CACHE_PATH.read_text(
                encoding="utf-8"
            )

            self.cache.deserialize(cache_content)

    def _save_cache(self):
        """Guarda la sesión cuando MSAL realiza cambios."""

        if not self.cache.has_state_changed:
            return

        CACHE_PATH.write_text(
            self.cache.serialize(),
            encoding="utf-8",
        )

        # En Linux/Raspberry Pi, solo el propietario podrá leerlo.
        if os.name == "posix":
            CACHE_PATH.chmod(0o600)

    def login(self):
        """
        Intenta autenticarse usando la caché.

        Si no existe una sesión válida, utiliza Device Flow.
        """

        accounts = self.app.get_accounts()

        if accounts:
            result = self.app.acquire_token_silent(
                scopes=SCOPES,
                account=accounts[0],
            )

            if result and "access_token" in result:
                self._save_cache()

                print(
                    "Autenticación recuperada desde caché."
                )

                return result

        flow = self.app.initiate_device_flow(
            scopes=SCOPES
        )

        if "user_code" not in flow:
            raise RuntimeError(
                f"No se pudo iniciar Device Flow: {flow}"
            )

        print("=" * 60)
        print(flow["message"])
        print("=" * 60)

        result = self.app.acquire_token_by_device_flow(
            flow
        )

        self._save_cache()

        if "access_token" not in result:
            error = result.get(
                "error_description",
                result,
            )

            raise RuntimeError(
                f"Error autenticando: {error}"
            )

        print(
            "Autenticación realizada y guardada en caché."
        )

        return result