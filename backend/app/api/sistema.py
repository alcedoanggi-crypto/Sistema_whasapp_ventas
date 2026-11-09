from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import credenciales_validas, crear_token, usuario_actual
from app.config import settings
from app.db import get_db
from app.models import EventoWebhook

router = APIRouter(prefix="/api", tags=["sistema"])


class Login(BaseModel):
    email: str
    password: str


@router.post("/auth/login")
def login(datos: Login):
    if not credenciales_validas(datos.email, datos.password):
        raise HTTPException(401, "Credenciales incorrectas")
    return {"token": crear_token(datos.email), "email": datos.email}


@router.get("/sistema", dependencies=[Depends(usuario_actual)])
def estado():
    return {
        "modo": "sandbox" if settings.sandbox else "cloud",
        "api_version": settings.whatsapp_api_version,
        "phone_number_id_configurado": bool(settings.whatsapp_phone_number_id),
        "token_configurado": bool(settings.whatsapp_token),
        "rate_limit_mps": settings.rate_limit_mps,
        "max_reintentos": settings.max_reintentos,
        "celery_eager": settings.celery_eager,
        "ventana_atribucion_dias": settings.ventana_atribucion_dias,
    }


@router.get("/webhook-eventos", dependencies=[Depends(usuario_actual)])
def eventos_webhook(limite: int = Query(100, le=500), tipo: str | None = None, db: Session = Depends(get_db)):
    q = select(EventoWebhook).order_by(EventoWebhook.id.desc()).limit(limite)
    if tipo:
        q = q.where(EventoWebhook.tipo == tipo)
    return [
        {
            "id": e.id,
            "origen": e.origen,
            "tipo": e.tipo,
            "wamid": e.wamid,
            "procesado": e.procesado,
            "error": e.error,
            "recibido_en": e.recibido_en,
            "payload": e.payload,
        }
        for e in db.scalars(q)
    ]
