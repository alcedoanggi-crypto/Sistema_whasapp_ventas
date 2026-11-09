from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, cast, Date, func, select
from sqlalchemy.orm import Session

from app.api.campanas import metricas_por_campana
from app.db import get_db
from app.models import Campana, Contacto, EventoNegocio, Mensaje, ahora

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


@router.get("")
def resumen(dias: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    desde = ahora() - timedelta(days=dias)
    proactivos = (Mensaje.direccion == "saliente", Mensaje.tipo == "plantilla", Mensaje.creado >= desde)

    def contar(*estados):
        return func.count(case((Mensaje.estado.in_(estados), 1)))

    enviados, entregados, leidos, fallidos, respondidos = db.execute(
        select(
            contar("aceptado", "enviado", "entregado", "leido"),
            contar("entregado", "leido"),
            contar("leido"),
            contar("fallido"),
            func.count(Mensaje.respondido_en),
        ).where(*proactivos)
    ).one()

    conversiones, ingresos = db.execute(
        select(func.count(), func.coalesce(func.sum(EventoNegocio.monto), 0)).where(
            EventoNegocio.tipo == "compra", EventoNegocio.campana_id.is_not(None), EventoNegocio.creado >= desde
        )
    ).one()

    dia = cast(func.timezone("UTC", Mensaje.creado), Date)
    serie = db.execute(
        select(dia, func.count(), contar("entregado", "leido"), contar("leido"))
        .where(*proactivos)
        .group_by(dia)
        .order_by(dia)
    ).all()

    campanas = list(db.scalars(select(Campana).where(Campana.iniciada.is_not(None)).order_by(Campana.iniciada.desc()).limit(10)))
    metricas = metricas_por_campana(db, [c.id for c in campanas])

    entrantes = db.scalar(select(func.count()).where(Mensaje.direccion == "entrante", Mensaje.creado >= desde))
    return {
        "periodo_dias": dias,
        "kpis": {
            "enviados": enviados,
            "entregados": entregados,
            "leidos": leidos,
            "fallidos": fallidos,
            "respondidos": respondidos,
            "tasa_entrega": _pct(entregados, enviados + fallidos),
            "tasa_lectura": _pct(leidos, entregados),
            "tasa_respuesta": _pct(respondidos, entregados),
            "conversiones": conversiones,
            "ingresos": float(ingresos),
            "mensajes_recibidos": entrantes,
        },
        "contactos": {
            "total": db.scalar(select(func.count(Contacto.id))),
            "con_opt_in": db.scalar(select(func.count()).where(Contacto.opt_in.is_(True))),
            "bajas_periodo": db.scalar(select(func.count()).where(Contacto.opt_out_fecha >= desde)),
        },
        "serie": [{"dia": d.isoformat(), "enviados": n, "entregados": e, "leidos": l} for d, n, e, l in serie],
        "campanas": [
            {"id": c.id, "nombre": c.nombre, "estado": c.estado, "iniciada": c.iniciada, **(metricas.get(c.id) or {})}
            for c in campanas
        ],
    }
