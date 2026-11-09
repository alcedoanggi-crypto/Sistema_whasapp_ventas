from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Campana, Disparador, Plantilla
from app.schemas import PlantillaIn, PlantillaOut
from app.services import plantillas as tpl
from app.services.webhook import ESTADOS_PLANTILLA_META
from app.whatsapp.client import WhatsAppError, get_client

router = APIRouter(prefix="/api/plantillas", tags=["plantillas"])


def _out(p: Plantilla) -> PlantillaOut:
    out = PlantillaOut.model_validate(p)
    out.variables = tpl.extraer_variables(p.encabezado, p.cuerpo)
    return out


@router.get("")
def listar(estado: str | None = None, db: Session = Depends(get_db)):
    q = select(Plantilla).order_by(Plantilla.actualizado.desc())
    if estado:
        q = q.where(Plantilla.estado == estado)
    return [_out(p) for p in db.scalars(q)]


@router.post("", status_code=201)
def crear(datos: PlantillaIn, db: Session = Depends(get_db)):
    if db.scalar(select(Plantilla.id).where(Plantilla.nombre == datos.nombre)):
        raise HTTPException(409, "Ya existe una plantilla con ese nombre")
    p = Plantilla(**datos.model_dump())
    db.add(p)
    db.commit()
    return _out(p)


@router.get("/{plantilla_id}")
def detalle(plantilla_id: int, db: Session = Depends(get_db)):
    return _out(_obtener(db, plantilla_id))


@router.put("/{plantilla_id}")
def actualizar(plantilla_id: int, datos: PlantillaIn, db: Session = Depends(get_db)):
    p = _obtener(db, plantilla_id)
    if p.estado in ("PENDIENTE", "APROBADA"):
        # En Meta, editar una plantilla aprobada la devuelve a revisión; aquí obligamos a crear una nueva versión.
        raise HTTPException(409, "Una plantilla enviada a Meta no se edita: duplícala con otro nombre")
    for campo, valor in datos.model_dump().items():
        setattr(p, campo, valor)
    p.estado, p.motivo_rechazo = "BORRADOR", None
    db.commit()
    return _out(p)


@router.delete("/{plantilla_id}", status_code=204)
def eliminar(plantilla_id: int, db: Session = Depends(get_db)):
    p = _obtener(db, plantilla_id)
    if db.scalar(select(Campana.id).where(Campana.plantilla_id == p.id).limit(1)):
        raise HTTPException(409, "La plantilla está usada en campañas")
    db.query(Disparador).filter(Disparador.plantilla_id == p.id).update({"plantilla_id": None, "activo": False})
    db.delete(p)
    db.commit()


@router.post("/{plantilla_id}/enviar-a-meta")
def enviar_a_meta(plantilla_id: int, db: Session = Depends(get_db)):
    """Registra la plantilla en la WABA para revisión. En sandbox se aprueba al instante."""
    p = _obtener(db, plantilla_id)
    if p.estado not in ("BORRADOR", "RECHAZADA"):
        raise HTTPException(409, f"La plantilla ya está {p.estado}")
    try:
        r = get_client().registrar_plantilla(p.nombre, p.idioma, p.categoria, tpl.componentes_registro(p))
    except WhatsAppError as exc:
        raise HTTPException(502, f"Meta rechazó la solicitud: {exc}")
    p.meta_id = r.get("id")
    p.estado = ESTADOS_PLANTILLA_META.get(r.get("status"), "PENDIENTE")
    p.motivo_rechazo = None
    db.commit()
    return _out(p)


@router.post("/{plantilla_id}/sincronizar")
def sincronizar(plantilla_id: int, db: Session = Depends(get_db)):
    """Consulta el estado en Meta (además, Meta lo notifica por webhook: message_template_status_update)."""
    p = _obtener(db, plantilla_id)
    try:
        r = get_client().estado_plantilla(p.nombre)
    except WhatsAppError as exc:
        raise HTTPException(502, str(exc))
    if r:
        p.estado = ESTADOS_PLANTILLA_META.get(r.get("status"), p.estado)
        p.motivo_rechazo = r.get("rejected_reason") if p.estado == "RECHAZADA" else None
        db.commit()
    return _out(p)


@router.post("/vista-previa")
def vista_previa(datos: PlantillaIn):
    """Lo que se enviaría a Meta, renderizado con los valores de ejemplo."""
    valores = datos.ejemplos or {}
    return {
        "variables": tpl.extraer_variables(datos.encabezado, datos.cuerpo),
        "encabezado": tpl.renderizar(datos.encabezado, valores),
        "cuerpo": tpl.renderizar(datos.cuerpo, valores),
        "componentes_meta": tpl.componentes_registro(Plantilla(**datos.model_dump())),
        "modo": "sandbox" if settings.sandbox else "cloud",
    }


def _obtener(db: Session, plantilla_id: int) -> Plantilla:
    p = db.get(Plantilla, plantilla_id)
    if p is None:
        raise HTTPException(404, "Plantilla no encontrada")
    return p
