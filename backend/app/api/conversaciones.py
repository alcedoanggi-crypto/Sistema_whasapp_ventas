from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Contacto, Mensaje, Plantilla
from app.schemas import ContactoOut, MensajeOut, PlantillaEnvioIn, TextoIn
from app.services import envio
from app.services.envio import EnvioNoPermitido, ventana_abierta
from app.tasks import simular_respuesta

router = APIRouter(prefix="/api/conversaciones", tags=["conversaciones"])


@router.get("")
def bandeja(q: str | None = None, solo_no_leidos: bool = False, db: Session = Depends(get_db)):
    consulta = select(Contacto).where(Contacto.ultimo_mensaje.is_not(None))
    if q:
        consulta = consulta.where(or_(Contacto.nombre.ilike(f"%{q}%"), Contacto.telefono.like(f"%{q}%")))
    if solo_no_leidos:
        consulta = consulta.where(Contacto.no_leidos > 0)
    contactos = list(db.scalars(consulta.order_by(Contacto.ultimo_mensaje.desc()).limit(100)))

    # Último mensaje de cada conversación en una sola consulta (DISTINCT ON de PostgreSQL)
    ultimos = {
        m.contacto_id: m
        for m in db.scalars(
            select(Mensaje)
            .where(Mensaje.contacto_id.in_([c.id for c in contactos]))
            .distinct(Mensaje.contacto_id)
            .order_by(Mensaje.contacto_id, Mensaje.creado.desc())
        )
    }
    return [
        {
            "contacto": ContactoOut.model_validate(c),
            "ventana_abierta": ventana_abierta(c),
            "ultimo": MensajeOut.model_validate(ultimos[c.id]) if c.id in ultimos else None,
        }
        for c in contactos
    ]


@router.get("/{contacto_id}")
def hilo(contacto_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, contacto_id)
    mensajes = db.scalars(
        select(Mensaje).where(Mensaje.contacto_id == c.id).order_by(Mensaje.creado.desc()).limit(200)
    ).all()
    return {
        "contacto": ContactoOut.model_validate(c),
        "ventana_abierta": ventana_abierta(c),
        "mensajes": [MensajeOut.model_validate(m) for m in reversed(mensajes)],
    }


@router.post("/{contacto_id}/leido", status_code=204)
def marcar_leido(contacto_id: int, db: Session = Depends(get_db)):
    _obtener(db, contacto_id).no_leidos = 0
    db.commit()


@router.post("/{contacto_id}/texto", response_model=MensajeOut, status_code=201)
def responder(contacto_id: int, datos: TextoIn, db: Session = Depends(get_db)):
    try:
        return envio.enviar_texto(db, _obtener(db, contacto_id), datos.texto, origen="manual")
    except EnvioNoPermitido as exc:
        raise HTTPException(409, str(exc))


@router.post("/{contacto_id}/plantilla", response_model=MensajeOut, status_code=201)
def enviar_plantilla(contacto_id: int, datos: PlantillaEnvioIn, db: Session = Depends(get_db)):
    """Para retomar una conversación con la ventana de 24 h cerrada."""
    p = db.get(Plantilla, datos.plantilla_id)
    if p is None:
        raise HTTPException(404, "Plantilla no encontrada")
    try:
        return envio.enviar_plantilla(db, _obtener(db, contacto_id), p, datos.variables, origen="manual")
    except EnvioNoPermitido as exc:
        raise HTTPException(409, str(exc))


@router.post("/{contacto_id}/simular-entrante", status_code=202)
def simular_entrante(contacto_id: int, datos: TextoIn, db: Session = Depends(get_db)):
    """Solo sandbox: inyecta un mensaje del cliente como si llegara por el webhook de Meta."""
    if not settings.sandbox:
        raise HTTPException(403, "Disponible solo en modo sandbox")
    c = _obtener(db, contacto_id)
    simular_respuesta.delay(c.telefono, datos.texto, c.nombre)
    return {"ok": True}


def _obtener(db: Session, contacto_id: int) -> Contacto:
    c = db.get(Contacto, contacto_id)
    if c is None:
        raise HTTPException(404, "Contacto no encontrado")
    return c
