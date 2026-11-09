from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Campana, EventoNegocio, Mensaje, Plantilla, ahora
from app.schemas import CampanaIn, CampanaOut, MensajeOut, Segmento
from app.services import campanas as svc
from app.tasks import lanzar_campana

router = APIRouter(prefix="/api/campanas", tags=["campanas"])


def metricas_por_campana(db: Session, ids: list[int] | None = None) -> dict[int, dict]:
    def contar(*estados):
        return func.count(case((Mensaje.estado.in_(estados), 1)))

    q = select(
        Mensaje.campana_id,
        func.count(),
        contar("en_cola", "enviando"),
        contar("aceptado", "enviado", "entregado", "leido"),
        contar("entregado", "leido"),
        contar("leido"),
        contar("fallido"),
        func.count(Mensaje.respondido_en),
    ).where(Mensaje.campana_id.is_not(None))
    if ids is not None:
        q = q.where(Mensaje.campana_id.in_(ids))
    filas = db.execute(q.group_by(Mensaje.campana_id)).all()

    conv_q = select(EventoNegocio.campana_id, func.count(), func.coalesce(func.sum(EventoNegocio.monto), 0)).where(
        EventoNegocio.tipo == "compra", EventoNegocio.campana_id.is_not(None)
    )
    conversiones = {cid: (n, float(m)) for cid, n, m in db.execute(conv_q.group_by(EventoNegocio.campana_id))}

    def pct(a, b):
        return round(100 * a / b, 1) if b else 0.0

    res = {}
    for cid, total, cola, enviados, entregados, leidos, fallidos, respondidos in filas:
        n_conv, ingresos = conversiones.get(cid, (0, 0.0))
        res[cid] = {
            "total": total,
            "en_cola": cola,
            "enviados": enviados,
            "entregados": entregados,
            "leidos": leidos,
            "fallidos": fallidos,
            "respondidos": respondidos,
            "conversiones": n_conv,
            "ingresos": ingresos,
            "tasa_entrega": pct(entregados, enviados + fallidos),
            "tasa_lectura": pct(leidos, entregados),
            "tasa_respuesta": pct(respondidos, entregados),
            "tasa_conversion": pct(n_conv, entregados),
        }
    return res


def _out(c: Campana, metricas: dict) -> dict:
    return {
        **CampanaOut.model_validate(c).model_dump(),
        "plantilla": c.plantilla.nombre if c.plantilla else None,
        "metricas": metricas.get(c.id),
    }


@router.get("")
def listar(db: Session = Depends(get_db)):
    filas = list(db.scalars(select(Campana).order_by(Campana.creado.desc())))
    m = metricas_por_campana(db, [c.id for c in filas])
    return [_out(c, m) for c in filas]


@router.post("/segmento/contar")
def contar_segmento(segmento: Segmento, db: Session = Depends(get_db)):
    return {"contactos": svc.contar_segmento(db, segmento.model_dump())}


@router.post("", status_code=201)
def crear(datos: CampanaIn, db: Session = Depends(get_db)):
    if db.get(Plantilla, datos.plantilla_id) is None:
        raise HTTPException(404, "Plantilla no encontrada")
    c = Campana(
        nombre=datos.nombre,
        plantilla_id=datos.plantilla_id,
        segmento=datos.segmento.model_dump(),
        variables=datos.variables,
    )
    db.add(c)
    db.flush()
    if datos.programada_para:
        _programar(db, c, datos.programada_para)
    db.commit()
    return _out(c, {})


@router.get("/{campana_id}")
def detalle(campana_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, campana_id)
    mensajes = db.scalars(select(Mensaje).where(Mensaje.campana_id == c.id).order_by(Mensaje.id.desc()).limit(200))
    return {
        **_out(c, metricas_por_campana(db, [c.id])),
        "errores": svc.validar(c),
        "audiencia_estimada": svc.contar_segmento(db, c.segmento),
        "mensajes": [
            {**MensajeOut.model_validate(m).model_dump(), "contacto": m.contacto.nombre or m.contacto.telefono}
            for m in mensajes
        ],
    }


@router.post("/{campana_id}/programar")
def programar(campana_id: int, cuando: dict, db: Session = Depends(get_db)):
    from datetime import datetime

    c = _obtener(db, campana_id)
    try:
        fecha = datetime.fromisoformat(cuando["programada_para"])
    except (KeyError, ValueError):
        raise HTTPException(422, "programada_para debe ser una fecha ISO 8601")
    _programar(db, c, fecha)
    db.commit()
    return _out(c, {})


@router.post("/{campana_id}/lanzar")
def lanzar_ahora(campana_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, campana_id)
    if c.estado not in ("BORRADOR", "PROGRAMADA"):
        raise HTTPException(409, f"La campaña está {c.estado}")
    if errores := svc.validar(c):
        raise HTTPException(422, " · ".join(errores))
    c.estado, c.programada_para, c.iniciada, c.total_destinatarios = "EN_CURSO", ahora(), ahora(), None
    db.commit()
    lanzar_campana.delay(c.id)
    return _out(c, {})


@router.post("/{campana_id}/cancelar")
def cancelar(campana_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, campana_id)
    if c.estado in ("COMPLETADA", "CANCELADA"):
        raise HTTPException(409, f"La campaña ya está {c.estado}")
    c.estado = "CANCELADA"
    # Lo que aún no salió no se envía.
    db.query(Mensaje).filter(Mensaje.campana_id == c.id, Mensaje.estado == "en_cola").update(
        {"estado": "fallido", "error": "Campaña cancelada", "fallido_en": ahora()}
    )
    db.commit()
    return _out(c, {})


def _programar(db: Session, c: Campana, fecha) -> None:
    if c.estado not in ("BORRADOR", "PROGRAMADA"):
        raise HTTPException(409, f"La campaña está {c.estado}")
    if fecha.tzinfo is None:
        raise HTTPException(422, "La fecha debe incluir zona horaria")
    if errores := svc.validar(c):
        raise HTTPException(422, " · ".join(errores))
    c.estado, c.programada_para = "PROGRAMADA", fecha


def _obtener(db: Session, campana_id: int) -> Campana:
    c = db.get(Campana, campana_id)
    if c is None:
        raise HTTPException(404, "Campaña no encontrada")
    return c
