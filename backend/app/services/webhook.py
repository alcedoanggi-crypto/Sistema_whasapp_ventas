"""Procesamiento de notificaciones del webhook de la Cloud API.

Flujo: el endpoint guarda cada notificación en `eventos_webhook` y responde 200 de inmediato
(Meta reintenta si tardamos); un worker procesa luego cada evento con `procesar_evento`.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contacto, EventoWebhook, Mensaje, Plantilla, RespuestaAutomatica, ahora
from app.services import consentimientos, envio
from app.services import plantillas as tpl

ESTADOS_META = {"sent": "enviado", "delivered": "entregado", "read": "leido", "failed": "fallido"}
ORDEN = {"en_cola": 0, "enviando": 0, "aceptado": 1, "enviado": 2, "entregado": 3, "leido": 4}

PALABRAS_BAJA = {"BAJA", "STOP", "DETENER", "CANCELAR", "UNSUBSCRIBE", "NO MAS MENSAJES", "DARME DE BAJA"}
PALABRAS_ALTA = {"ALTA", "START", "SUSCRIBIRME"}
VENTANA_RESPUESTA = timedelta(hours=72)

ESTADOS_PLANTILLA_META = {"APPROVED": "APROBADA", "REJECTED": "RECHAZADA", "PENDING": "PENDIENTE"}


class MensajeNoEncontrado(Exception):
    """El estado llegó antes de que se guardara el wamid; la tarea se reintenta."""


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", sin_tildes)).strip().upper()


def registrar_payload(db: Session, payload: dict, origen: str = "meta") -> list[int]:
    """Divide la notificación en eventos atómicos (un estado o un mensaje cada uno)."""
    eventos: list[EventoWebhook] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if change.get("field") == "message_template_status_update":
                eventos.append(EventoWebhook(origen=origen, tipo="template_status", payload=value))
                continue
            for st in value.get("statuses", []):
                eventos.append(EventoWebhook(origen=origen, tipo="status", wamid=st.get("id"), payload=st))
            for msg in value.get("messages", []):
                eventos.append(
                    EventoWebhook(
                        origen=origen,
                        tipo="message",
                        wamid=msg.get("id"),
                        payload={"message": msg, "contacts": value.get("contacts", [])},
                    )
                )
    if not eventos:
        eventos.append(EventoWebhook(origen=origen, tipo="otro", payload=payload, procesado=True))
    db.add_all(eventos)
    db.commit()
    return [e.id for e in eventos if not e.procesado]


def procesar_evento(db: Session, evento_id: int) -> None:
    ev = db.get(EventoWebhook, evento_id)
    if ev is None or ev.procesado:
        return
    if ev.tipo == "status":
        _procesar_estado(db, ev.payload)
    elif ev.tipo == "message":
        _procesar_entrante(db, ev.payload["message"], ev.payload.get("contacts", []))
    elif ev.tipo == "template_status":
        _procesar_estado_plantilla(db, ev.payload)
    ev.procesado = True
    ev.error = None
    db.commit()


def _ts(valor) -> datetime:
    try:
        return datetime.fromtimestamp(int(valor), tz=timezone.utc)
    except (TypeError, ValueError):
        return ahora()


def _procesar_estado(db: Session, st: dict) -> None:
    m = db.scalar(select(Mensaje).where(Mensaje.wamid == st["id"]))
    if m is None:
        raise MensajeNoEncontrado(st["id"])
    nuevo = ESTADOS_META.get(st.get("status"))
    if nuevo is None:
        return
    ts = _ts(st.get("timestamp"))

    if nuevo == "fallido":
        # Un "failed" tardío no pisa un mensaje que ya consta como entregado o leído.
        if m.estado not in ("entregado", "leido"):
            err = (st.get("errors") or [{}])[0]
            detalle = (err.get("error_data") or {}).get("details") or err.get("message") or ""
            m.estado, m.fallido_en = "fallido", ts
            m.error_codigo = err.get("code")
            m.error = f"[{err.get('code')}] {err.get('title', 'Error')}. {detalle}".strip()
        return

    # Los webhooks pueden llegar desordenados (p. ej. "read" antes que "delivered"):
    # completamos las marcas de tiempo implícitas y el estado solo avanza.
    m.enviado_en = m.enviado_en or ts
    if nuevo in ("entregado", "leido"):
        m.entregado_en = m.entregado_en or ts
    if nuevo == "leido":
        m.leido_en = m.leido_en or ts
    if m.estado == "fallido" or ORDEN[nuevo] > ORDEN.get(m.estado, 0):
        m.estado = nuevo


def _texto_de(msg: dict) -> str:
    tipo = msg.get("type")
    if tipo == "text":
        return msg["text"]["body"]
    if tipo == "button":
        return msg["button"].get("text", "")
    if tipo == "interactive":
        inter = msg["interactive"]
        return (inter.get("button_reply") or inter.get("list_reply") or {}).get("title", "")
    return f"[{tipo}]"


def _procesar_entrante(db: Session, msg: dict, contacts: list[dict]) -> None:
    if db.scalar(select(Mensaje.id).where(Mensaje.wamid == msg["id"])):
        return  # Meta reenvía notificaciones: deduplicamos por wamid

    telefono = msg["from"]
    perfil = (contacts[0].get("profile", {}) if contacts else {}).get("name", "")
    contacto = db.scalar(select(Contacto).where(Contacto.telefono == telefono))
    if contacto is None:
        # Que alguien nos escriba NO equivale a opt-in de marketing: se crea sin consentimiento.
        contacto = Contacto(telefono=telefono, nombre=perfil, etiquetas=["entrante"], opt_in=False)
        db.add(contacto)

    ts = _ts(msg.get("timestamp"))
    texto = _texto_de(msg)
    db.add(
        Mensaje(
            contacto=contacto,
            origen="cliente",
            direccion="entrante",
            tipo=msg.get("type", "text"),
            contenido=texto,
            wamid=msg["id"],
            estado="recibido",
            creado=ts,
        )
    )
    contacto.ultimo_entrante = ts
    contacto.ultimo_mensaje = ts
    contacto.no_leidos = (contacto.no_leidos or 0) + 1
    db.flush()

    # Tasa de respuesta: se atribuye al último mensaje proactivo (campaña/disparador) de las últimas 72 h.
    previo = db.scalar(
        select(Mensaje)
        .where(
            Mensaje.contacto_id == contacto.id,
            Mensaje.direccion == "saliente",
            Mensaje.tipo == "plantilla",
            Mensaje.respondido_en.is_(None),
            Mensaje.creado >= ts - VENTANA_RESPUESTA,
        )
        .order_by(Mensaje.creado.desc())
        .limit(1)
    )
    if previo:
        previo.respondido_en = ts

    comando = normalizar(texto)
    nombre = tpl.variables_de_contacto(contacto)["nombre"]
    respuesta, origen = None, "sistema"
    if comando in PALABRAS_BAJA:
        if contacto.opt_in:
            consentimientos.registrar_opt_out(
                db, contacto, "palabra_clave", f'Respondió "{texto}" (wamid {msg["id"]})', ts
            )
        respuesta = (
            f"Listo, {nombre}. Ya no recibirás mensajes promocionales. "
            "Si cambias de opinión, escribe ALTA."
        )
    elif comando in PALABRAS_ALTA:
        consentimientos.registrar_opt_in(db, contacto, "whatsapp", f'Escribió "{texto}" (wamid {msg["id"]})', ts)
        respuesta = f"¡Gracias, {nombre}! Te suscribiste a nuestras novedades. Escribe BAJA cuando quieras salir."
    elif regla := buscar_respuesta_automatica(db, comando):
        regla.coincidencias += 1
        respuesta, origen = tpl.renderizar(regla.respuesta, tpl.variables_de_contacto(contacto)), "auto_respuesta"
    db.commit()

    if respuesta:
        envio.enviar_texto(db, contacto, respuesta, origen=origen)


def buscar_respuesta_automatica(db: Session, texto_normalizado: str) -> RespuestaAutomatica | None:
    palabras = f" {texto_normalizado} "
    reglas = db.scalars(
        select(RespuestaAutomatica)
        .where(RespuestaAutomatica.activo.is_(True))
        .order_by(RespuestaAutomatica.prioridad.desc(), RespuestaAutomatica.id)
    )
    for regla in reglas:
        if any(f" {normalizar(k)} " in palabras for k in regla.palabras_clave):
            return regla
    return None


def _procesar_estado_plantilla(db: Session, value: dict) -> None:
    p = db.scalar(select(Plantilla).where(Plantilla.nombre == value.get("message_template_name")))
    if p is None:
        return
    p.estado = ESTADOS_PLANTILLA_META.get(value.get("event"), p.estado)
    p.motivo_rechazo = value.get("reason") if p.estado == "RECHAZADA" else None
