"""Payloads con la misma forma que los webhooks reales de Meta.

El sandbox no tiene un camino alternativo: genera estas notificaciones y las pasa por el
mismo `services.webhook`, de modo que la demo ejercita exactamente el código de producción.
"""
import time
import uuid

from app.config import settings


def _envoltorio(value: dict) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": settings.whatsapp_business_account_id or "SANDBOX_WABA",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": settings.whatsapp_phone_number_id or "SANDBOX_PHONE",
                            },
                            **value,
                        },
                    }
                ],
            }
        ],
    }


def payload_estado(wamid: str, estado: str, telefono: str, error: dict | None = None) -> dict:
    st = {"id": wamid, "status": estado, "timestamp": str(int(time.time())), "recipient_id": telefono}
    if error:
        st["errors"] = [error]
    return _envoltorio({"statuses": [st]})


def payload_mensaje(telefono: str, texto: str, nombre: str = "") -> dict:
    return _envoltorio(
        {
            "contacts": [{"profile": {"name": nombre}, "wa_id": telefono}],
            "messages": [
                {
                    "from": telefono,
                    "id": f"wamid.SANDBOX.IN.{uuid.uuid4().hex}",
                    "timestamp": str(int(time.time())),
                    "type": "text",
                    "text": {"body": texto},
                }
            ],
        }
    )
