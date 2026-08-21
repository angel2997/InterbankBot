import requests

from services.auth_service import AuthService

auth = AuthService()

token = auth.login()

access_token = token["access_token"]

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "https://graph.microsoft.com/v1.0/me",
    headers=headers
)

print(response.json())