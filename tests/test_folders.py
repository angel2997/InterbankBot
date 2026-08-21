import requests

from services.auth_service import AuthService


def print_response(response):
    print("STATUS:", response.status_code)
    print("BODY:")
    print(response.text)

    print("\nWWW-AUTHENTICATE:")
    print(response.headers.get("WWW-Authenticate"))

    print("\nHEADERS:")
    for key, value in response.headers.items():
        if key.lower() != "authorization":
            print(f"{key}: {value}")


# ============================================================
# LOGIN
# ============================================================

auth = AuthService()

print("=" * 60)
print("AUTENTICANDO")
print("=" * 60)

token = auth.login()

print("\nTOKEN KEYS:")
print(token.keys())


# ============================================================
# VALIDAR TOKEN
# ============================================================

access_token = token.get("access_token")

if not access_token:
    print("\nERROR: No se obtuvo access_token")
    print(token)
    raise SystemExit(1)

print("\nACCESS TOKEN LENGTH:")
print(len(access_token))

print("\nSCOPES DEL TOKEN:")
print(token.get("scope"))


# ============================================================
# MOSTRAR DATOS DEL ID TOKEN
# ============================================================

print("\n" + "=" * 60)
print("DATOS DEL USUARIO AUTENTICADO")
print("=" * 60)

claims = token.get("id_token_claims", {})

print("name:")
print(claims.get("name"))

print("\npreferred_username:")
print(claims.get("preferred_username"))

print("\ntid:")
print(claims.get("tid"))

print("\niss:")
print(claims.get("iss"))

print("\naud:")
print(claims.get("aud"))

print("\nemail:")
print(claims.get("email"))


# ============================================================
# HEADERS
# ============================================================

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}


# ============================================================
# PRUEBA 1 - PERFIL
# ============================================================

print("\n" + "=" * 60)
print("PRUEBA 1: PERFIL")
print("=" * 60)

response = requests.get(
    "https://graph.microsoft.com/v1.0/me",
    headers=headers
)

print_response(response)


# ============================================================
# PRUEBA 2 - MENSAJES
# ============================================================

print("\n" + "=" * 60)
print("PRUEBA 2: MENSAJES")
print("=" * 60)

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/messages?$top=1",
    headers=headers
)

print_response(response)


# ============================================================
# PRUEBA 3 - CARPETAS
# ============================================================

print("\n" + "=" * 60)
print("PRUEBA 3: CARPETAS")
print("=" * 60)

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/mailFolders",
    headers=headers
)

print_response(response)


# ============================================================
# PRUEBA 4 - INBOX
# ============================================================

print("\n" + "=" * 60)
print("PRUEBA 4: INBOX")
print("=" * 60)

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/mailFolders/inbox",
    headers=headers
)

print_response(response)


# ============================================================
# FIN
# ============================================================

print("\n" + "=" * 60)
print("DIAGNÓSTICO FINALIZADO")
print("=" * 60)