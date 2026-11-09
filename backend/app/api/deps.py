import hmac
from datetime import timedelta

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models import ahora

ALGORITMO = "HS256"
_bearer = HTTPBearer(auto_error=False)


def crear_token(email: str) -> str:
    payload = {"sub": email, "exp": ahora() + timedelta(hours=12)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITMO)


def credenciales_validas(email: str, password: str) -> bool:
    return hmac.compare_digest(email.lower(), settings.admin_email.lower()) and hmac.compare_digest(
        password, settings.admin_password
    )


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    try:
        return jwt.decode(cred.credentials, settings.secret_key, algorithms=[ALGORITMO])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")


def integracion_o_usuario(
    x_api_key: str | None = Header(default=None),
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Para /api/eventos: lo llama el e-commerce con X-API-Key, o el panel con su token."""
    if x_api_key and hmac.compare_digest(x_api_key, settings.integration_api_key):
        return "integracion"
    return usuario_actual(cred)
