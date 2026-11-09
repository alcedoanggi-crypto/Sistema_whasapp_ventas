import hashlib
import hmac


def firmar(cuerpo: bytes, app_secret: str) -> str:
    return "sha256=" + hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()


def firma_valida(cuerpo: bytes, cabecera: str | None, app_secret: str) -> bool:
    """Valida X-Hub-Signature-256: HMAC-SHA256 del cuerpo *crudo* con el App Secret de la app de Meta.

    Se calcula sobre los bytes exactos recibidos (no sobre el JSON re-serializado) y se
    compara en tiempo constante para no filtrar información por tiempos de respuesta.
    """
    if not cabecera or not cabecera.startswith("sha256=") or not app_secret:
        return False
    return hmac.compare_digest(firmar(cuerpo, app_secret), cabecera)
