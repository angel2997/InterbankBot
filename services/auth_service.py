import os

from dotenv import load_dotenv
from msal import PublicClientApplication

load_dotenv()

CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")

SCOPES = [
    "User.Read",
    "Mail.Read"
]


class AuthService:

    def __init__(self):

        self.app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority="https://login.microsoftonline.com/consumers"
        )

    def login(self):

        flow = self.app.initiate_device_flow(
            scopes=SCOPES
        )

        if "user_code" not in flow:
            raise Exception(
                f"No se pudo iniciar Device Flow: {flow}"
            )

        print("=" * 60)
        print(flow["message"])
        print("=" * 60)

        result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise Exception(
                f"Error autenticando: {result}"
            )

        return result