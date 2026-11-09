from datetime import timedelta

from sqlalchemy import exists, func, select, update
from sqlalchemy.orm import Session

from app.models import Campana, Contacto, Mensaje, ahora
from app.services import envio
from app.services import plantillas as tpl

LOTE = 200


def consulta_segmento(segmento: dict | None):
    segmento = segmento or {}
    q = select(Contacto).where(Contacto.opt_in.is_(True))  # el opt-in no es opcional
    if etiquetas := segmento.get("etiquetas"):
        if segmento.get("modo") == "todas":
            q = q.where(Contacto.etiquetas.contains(etiquetas))
        else:
            q = q.where(Contacto.etiquetas.overlap(etiquetas))
    return q


def contar_segmento(db: Session, segmento: dict | None) -> int:
    return db.scalar(select(func.count()).select_from(consulta_segmento(segmento).subquery()))


def validar(campana: Campana) -> list[str]:
    errores = []
    p = campana.plantilla
    if p is None:
        return ["Selecciona una plantilla"]
    if p.estado != "APROBADA":
        errores.append(f"La plantilla '{p.nombre}' aún no está aprobada por Meta")
    requeridas = set(tpl.extraer_variables(p.encabezado, p.cuerpo)) - tpl.VARIABLES_DE_CONTACTO
    if faltan := sorted(v for v in requeridas if not str((campana.variables or {}).get(v, "")).strip()):
        errores.append(f"Define un valor para: {', '.join(faltan)}")
    return errores


def tomar_vencidas(db: Session) -> list[int]:
    """Pasa a EN_CURSO, de forma atómica, las campañas programadas cuya hora ya llegó."""
    ids = list(
        db.scalars(
            update(Campana)
            .where(Campana.estado == "PROGRAMADA", Campana.programada_para <= ahora())
            .values(estado="EN_CURSO", iniciada=ahora(), total_destinatarios=None)
            .returning(Campana.id)
        )
    )
    db.commit()
    return ids


def lanzamientos_interrumpidos(db: Session) -> list[int]:
    """EN_CURSO sin total tras 5 min: la tarea de lanzamiento se perdió o murió a medias."""
    return list(
        db.scalars(
            select(Campana.id).where(
                Campana.estado == "EN_CURSO",
                Campana.total_destinatarios.is_(None),
                Campana.iniciada < ahora() - timedelta(minutes=5),
            )
        )
    )


def lanzar(db: Session, campana_id: int) -> int:
    """Crea y encola un mensaje por contacto del segmento. Idempotente: se puede reintentar."""
    c = db.get(Campana, campana_id)
    if c is None or c.estado != "EN_CURSO":
        return 0

    ya_enviados = set(db.scalars(select(Mensaje.contacto_id).where(Mensaje.campana_id == c.id)))
    creados, lote = 0, []
    for contacto in db.scalars(consulta_segmento(c.segmento).order_by(Contacto.id)).all():
        if contacto.id in ya_enviados:
            continue
        try:
            lote.append(
                envio.preparar_plantilla(db, contacto, c.plantilla, c.variables, origen="campana", campana_id=c.id)
            )
        except envio.EnvioNoPermitido:
            continue
        if len(lote) >= LOTE:
            creados += _confirmar_lote(db, lote)
            lote = []
    creados += _confirmar_lote(db, lote)

    c.total_destinatarios = db.scalar(select(func.count()).where(Mensaje.campana_id == c.id))
    db.commit()
    cerrar_completadas(db)
    return creados


def _confirmar_lote(db: Session, lote: list[Mensaje]) -> int:
    if not lote:
        return 0
    db.commit()
    envio.encolar([m.id for m in lote])
    return len(lote)


def cerrar_completadas(db: Session) -> None:
    pendiente = exists().where(Mensaje.campana_id == Campana.id, Mensaje.estado.in_(("en_cola", "enviando")))
    db.execute(
        update(Campana)
        .where(Campana.estado == "EN_CURSO", Campana.total_destinatarios.is_not(None), ~pendiente)
        .values(estado="COMPLETADA", finalizada=ahora())
        .execution_options(synchronize_session=False)
    )
    db.commit()
