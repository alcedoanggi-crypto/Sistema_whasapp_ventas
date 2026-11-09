"""Endpoint público que se registra en Meta (App Dashboard → WhatsApp → Configuración)."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.services import webhook
from app.tasks import procesar_evento_webhook
from app.whatsapp.firma import firma_valida

router = APIRouter(tags=["webhook"])
log = logging.getLogger(__name__)


@router.get("/webhook")
def verificar(
    modo: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    reto: str = Query(alias="hub.challenge"),
):
    """Handshake de suscripción: Meta envía un GET y espera recibir `hub.challenge` tal cual."""
    if modo == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=reto, media_type="text/plain")
    raise HTTPException(403, "Token de verificación incorrecto")


@router.post("/webhook")
async def recibir(request: Request, db: Session = Depends(get_db)):
    cuerpo = await request.body()  # bytes crudos: la firma se calcula sobre ellos
    if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256"), settings.whatsapp_app_secret):
        log.warning("Webhook rechazado: firma inválida desde %s", request.client.host if request.client else "?")
        raise HTTPException(401, "Firma inválida")
    try:
        payload = json.loads(cuerpo)
    except ValueError:
        raise HTTPException(400, "JSON inválido")

    ids = webhook.registrar_payload(db, payload, origen="meta")
    for evento_id in ids:
        procesar_evento_webhook.delay(evento_id)
    return {"recibidos": len(ids)}
