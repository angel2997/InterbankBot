import os
import requests

from dotenv import load_dotenv
from msal import PublicClientApplication

load_dotenv()

CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")

SCOPES = [
    "User.Read",
    "Mail.Read"
]


class AuthService:

    def login(self):

        app = PublicClientApplication(
            client_id=CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )

        flow = app.initiate_device_flow(
            scopes=SCOPES
        )

        if "user_code" not in flow:
            raise Exception(
                "No se pudo iniciar Device Flow"
            )

        print()
        print("=" * 60)
        print(flow["message"])
        print("=" * 60)
        print()

        result = app.acquire_token_by_device_flow(
            flow
        )

        return result