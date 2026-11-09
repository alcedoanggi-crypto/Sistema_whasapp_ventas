"""Disparadores automáticos alimentados por eventos de negocio.

Cada evento que puede disparar un mensaje queda `pendiente` con una fecha `disparo_en`;
la tarea periódica `procesar_programados` lo envía cuando vence. Así un retraso de días
no depende de que una tarea Celery con countdown sobreviva tanto tiempo en Redis.
"""
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Contacto, Disparador, EventoNegocio, Mensaje, ahora
from app.services import envio

EVENTO_A_DISPARADOR = {
    "alta": "bienvenida",
    "carrito_abandonado": "carrito_abandonado",
    "pago_pendiente": "recordatorio_pago",
    "compra": "post_venta",
}
TIPOS_EVENTO = set(EVENTO_A_DISPARADOR) | {"pago_realizado"}


def registrar_evento(
    db: Session,
    contacto: Contacto,
    tipo: str,
    referencia: str | None = None,
    datos: dict | None = None,
    monto: float | None = None,
) -> EventoNegocio:
    if tipo not in TIPOS_EVENTO:
        raise ValueError(f"Tipo de evento desconocido: {tipo}")
    ev = EventoNegocio(contacto=contacto, tipo=tipo, referencia=referencia, datos=datos or {}, monto=monto)
    db.add(ev)

    if tipo == "compra":
        # La compra cancela los recordatorios de carrito pendientes y se atribuye a una campaña.
        _cancelar(db, contacto.id, "carrito_abandonado", None, "El cliente completó la compra")
        ev.campana_id = _campana_atribuible(db, contacto.id)
    elif tipo == "pago_realizado":
        _cancelar(db, contacto.id, "pago_pendiente", referencia, "El pago se registró")

    if nombre_disparador := EVENTO_A_DISPARADOR.get(tipo):
        disp = db.scalar(select(Disparador).where(Disparador.tipo == nombre_disparador))
        if disp and disp.activo and disp.plantilla_id:
            ev.disparo_estado = "pendiente"
            ev.disparo_en = ahora() + timedelta(minutes=disp.retraso_minutos)
        else:
            ev.disparo_estado = "omitido"
            ev.disparo_detalle = "Disparador inactivo o sin plantilla"
    db.commit()

    if ev.disparo_estado == "pendiente" and ev.disparo_en <= ahora():
        from app.tasks import ejecutar_disparador

        ejecutar_disparador.delay(ev.id)
    return ev


def _cancelar(db: Session, contacto_id: int, tipo: str, referencia: str | None, motivo: str) -> None:
    condiciones = [
        EventoNegocio.contacto_id == contacto_id,
        EventoNegocio.tipo == tipo,
        EventoNegocio.disparo_estado == "pendiente",
    ]
    if referencia:
        condiciones.append(EventoNegocio.referencia == referencia)
    db.execute(update(EventoNegocio).where(*condiciones).values(disparo_estado="cancelado", disparo_detalle=motivo))


def _campana_atribuible(db: Session, contacto_id: int) -> int | None:
    """Atribución last-touch: la última campaña entregada al contacto dentro de la ventana."""
    desde = ahora() - timedelta(days=settings.ventana_atribucion_dias)
    return db.scalar(
        select(Mensaje.campana_id)
        .where(
            Mensaje.contacto_id == contacto_id,
            Mensaje.campana_id.is_not(None),
            Mensaje.estado.in_(("aceptado", "enviado", "entregado", "leido")),
            Mensaje.creado >= desde,
        )
        .order_by(Mensaje.creado.desc())
        .limit(1)
    )


def ejecutar(db: Session, evento_id: int) -> str:
    reclamado = db.execute(
        update(EventoNegocio)
        .where(EventoNegocio.id == evento_id, EventoNegocio.disparo_estado == "pendiente")
        .values(disparo_estado="procesando")
    ).rowcount
    db.commit()
    if not reclamado:
        return "omitido"

    ev = db.get(EventoNegocio, evento_id)
    disp = db.scalar(select(Disparador).where(Disparador.tipo == EVENTO_A_DISPARADOR[ev.tipo]))
    if not (disp and disp.activo and disp.plantilla):
        return _cerrar(db, ev, "omitido", "Disparador desactivado antes del envío")
    try:
        m = envio.preparar_plantilla(
            db, ev.contacto, disp.plantilla, ev.datos, origen="disparador", disparador=disp.tipo
        )
    except envio.EnvioNoPermitido as exc:
        return _cerrar(db, ev, "omitido", str(exc))
    ev.disparo_estado = "enviado"
    db.commit()
    envio.encolar([m.id])
    return "enviado"


def _cerrar(db: Session, ev: EventoNegocio, estado: str, detalle: str) -> str:
    ev.disparo_estado, ev.disparo_detalle = estado, detalle
    db.commit()
    return estado


def pendientes_vencidos(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(EventoNegocio.id).where(
                EventoNegocio.disparo_estado == "pendiente", EventoNegocio.disparo_en <= ahora()
            )
        )
    )
