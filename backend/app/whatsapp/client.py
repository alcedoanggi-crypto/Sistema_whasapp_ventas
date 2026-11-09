"""Cliente de la WhatsApp Business Cloud API (oficial de Meta) y su doble para sandbox.

Ambos exponen la misma interfaz, así que el resto del sistema no sabe en qué modo corre.
"""
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings

GRAPH_URL = "https://graph.facebook.com"

# Códigos de error de Meta que conviene reintentar (límites de velocidad y fallos temporales).
# https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
CODIGOS_REINTENTABLES = {1, 2, 4, 80007, 130429, 131000, 131016, 131056, 133004}


class WhatsAppError(Exception):
    def __init__(self, mensaje: str, codigo: int | None = None, reintentable: bool = False):
        super().__init__(mensaje)
        self.codigo = codigo
        self.reintentable = reintentable


@dataclass
class ResultadoEnvio:
    wamid: str


class CloudAPIClient:
    def __init__(self):
        self.base = f"{GRAPH_URL}/{settings.whatsapp_api_version}"
        self.headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}

    def _llamar(self, metodo: str, ruta: str, **kwargs) -> dict:
        try:
            r = httpx.request(metodo, f"{self.base}/{ruta}", headers=self.headers, timeout=15, **kwargs)
        except httpx.TransportError as exc:  # timeouts, DNS, conexión caída
            raise WhatsAppError(f"Error de red: {exc}", reintentable=True) from exc
        if r.is_success:
            return r.json()
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        codigo = err.get("code")
        detalle = (err.get("error_data") or {}).get("details") or err.get("message") or r.text
        reintentable = r.status_code == 429 or r.status_code >= 500 or codigo in CODIGOS_REINTENTABLES
        raise WhatsAppError(f"[{codigo or r.status_code}] {detalle}", codigo, reintentable)

    def enviar_plantilla(self, telefono: str, nombre: str, idioma: str, componentes: list[dict]) -> ResultadoEnvio:
        payload = {
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "template",
            "template": {"name": nombre, "language": {"code": idioma}, "components": componentes},
        }
        data = self._llamar("POST", f"{settings.whatsapp_phone_number_id}/messages", json=payload)
        return ResultadoEnvio(wamid=data["messages"][0]["id"])

    def enviar_texto(self, telefono: str, texto: str) -> ResultadoEnvio:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono,
            "type": "text",
            "text": {"preview_url": False, "body": texto},
        }
        data = self._llamar("POST", f"{settings.whatsapp_phone_number_id}/messages", json=payload)
        return ResultadoEnvio(wamid=data["messages"][0]["id"])

    def registrar_plantilla(self, nombre: str, idioma: str, categoria: str, componentes: list[dict]) -> dict:
        payload = {
            "name": nombre,
            "language": idioma,
            "category": categoria,
            "parameter_format": "NAMED",
            "components": componentes,
        }
        return self._llamar("POST", f"{settings.whatsapp_business_account_id}/message_templates", json=payload)

    def estado_plantilla(self, nombre: str) -> dict | None:
        data = self._llamar(
            "GET",
            f"{settings.whatsapp_business_account_id}/message_templates",
            params={"name": nombre, "fields": "id,name,status,rejected_reason"},
        )
        return (data.get("data") or [None])[0]


class SandboxClient:
    """No sale nada a internet. Devuelve wamids falsos; los estados los simula `tasks.simular_estados`."""

    def enviar_plantilla(self, telefono, nombre, idioma, componentes) -> ResultadoEnvio:
        return ResultadoEnvio(wamid=f"wamid.SANDBOX.{uuid.uuid4().hex}")

    def enviar_texto(self, telefono, texto) -> ResultadoEnvio:
        return ResultadoEnvio(wamid=f"wamid.SANDBOX.{uuid.uuid4().hex}")

    def registrar_plantilla(self, nombre, idioma, categoria, componentes) -> dict:
        return {"id": f"sandbox-{uuid.uuid4().hex[:12]}", "status": "APPROVED", "category": categoria}

    def estado_plantilla(self, nombre) -> dict | None:
        return {"status": "APPROVED"}


def get_client():
    return SandboxClient() if settings.sandbox else CloudAPIClient()
