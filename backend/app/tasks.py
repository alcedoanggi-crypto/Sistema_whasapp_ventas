import logging
import random
from datetime import timedelta

from sqlalchemy import select, update

from app.config import settings
from app.db import SessionLocal
from app.models import Mensaje, ahora
from app.services import campanas, disparadores, envio, webhook
from app.whatsapp import sandbox
from app.worker import celery

log = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=settings.max_reintentos + 2, acks_late=True)
def enviar_mensaje(self, mensaje_id: int) -> str:
    with SessionLocal() as db:
        try:
            return envio.ejecutar_envio(db, mensaje_id)
        except envio.ErrorReintentable as exc:
            # Backoff exponencial con jitter: 5s, 10s, 20s, 40s... (máx. 5 min)
            espera = min(300, 5 * 2**self.request.retries) + random.uniform(0, 3)
            log.warning("Reintento %s del mensaje %s en %.0fs: %s", self.request.retries + 1, mensaje_id, espera, exc)
            raise self.retry(exc=exc, countdown=espera)


@celery.task(bind=True, max_retries=5, acks_late=True)
def procesar_evento_webhook(self, evento_id: int) -> None:
    with SessionLocal() as db:
        try:
            webhook.procesar_evento(db, evento_id)
        except webhook.MensajeNoEncontrado as exc:
            raise self.retry(exc=exc, countdown=3 * (self.request.retries + 1))
        except Exception as exc:
            db.rollback()
            from app.models import EventoWebhook

            db.execute(update(EventoWebhook).where(EventoWebhook.id == evento_id).values(error=str(exc)[:2000]))
            db.commit()
            raise


@celery.task(acks_late=True)
def lanzar_campana(campana_id: int) -> int:
    with SessionLocal() as db:
        return campanas.lanzar(db, campana_id)


@celery.task(acks_late=True)
def ejecutar_disparador(evento_id: int) -> str:
    with SessionLocal() as db:
        return disparadores.ejecutar(db, evento_id)


@celery.task
def procesar_programados() -> None:
    """Tarea periódica (beat, cada 30 s)."""
    with SessionLocal() as db:
        for campana_id in campanas.tomar_vencidas(db) + campanas.lanzamientos_interrumpidos(db):
            lanzar_campana.delay(campana_id)
        for evento_id in disparadores.pendientes_vencidos(db):
            ejecutar_disparador.delay(evento_id)
        _rescatar_atascados(db)
        campanas.cerrar_completadas(db)


def _rescatar_atascados(db) -> None:
    """Re-encola mensajes cuya tarea se perdió (p. ej. Redis caído al encolar o worker muerto)."""
    limite = ahora() - timedelta(minutes=10)
    db.execute(
        update(Mensaje)
        .where(Mensaje.estado == "enviando", Mensaje.creado < limite)
        .values(estado="en_cola")
    )
    db.commit()
    ids = list(db.scalars(select(Mensaje.id).where(Mensaje.estado == "en_cola", Mensaje.creado < limite).limit(500)))
    envio.encolar(ids)  # el reclamo atómico de ejecutar_envio evita envíos duplicados


# ---------------------------------------------------------------- sandbox

FRASES_CLIENTE = [
    "Hola, ¿cuál es el precio?",
    "Me interesa, ¿tienen catálogo?",
    "¿Qué horarios tienen?",
    "¡Gracias!",
    "¿Hacen envíos a domicilio?",
]


def _inyectar(payload: dict) -> None:
    with SessionLocal() as db:
        ids = webhook.registrar_payload(db, payload, origen="sandbox")
    for evento_id in ids:
        procesar_evento_webhook.delay(evento_id)


@celery.task
def simular_estados(mensaje_id: int) -> None:
    """Imita el ciclo de vida que Meta notificaría: sent → delivered → read (o failed)."""
    with SessionLocal() as db:
        m = db.get(Mensaje, mensaje_id)
        if m is None or not m.wamid:
            return
        wamid, tel, proactivo = m.wamid, m.contacto.telefono, m.tipo == "plantilla"

    if proactivo and random.random() < 0.04:
        _inyectar(
            sandbox.payload_estado(
                wamid,
                "failed",
                tel,
                {
                    "code": 131026,
                    "title": "Message undeliverable",
                    "error_data": {"details": "Simulado: el número no tiene WhatsApp"},
                },
            )
        )
        return
    _inyectar(sandbox.payload_estado(wamid, "sent", tel))
    _inyectar(sandbox.payload_estado(wamid, "delivered", tel))
    if random.random() < 0.7:
        simular_lectura.apply_async((wamid, tel), countdown=random.randint(3, 10))
        if proactivo and random.random() < 0.25:
            texto = "BAJA" if random.random() < 0.08 else random.choice(FRASES_CLIENTE)
            simular_respuesta.apply_async((tel, texto), countdown=random.randint(8, 20))


@celery.task
def simular_lectura(wamid: str, telefono: str) -> None:
    _inyectar(sandbox.payload_estado(wamid, "read", telefono))


@celery.task
def simular_respuesta(telefono: str, texto: str, nombre: str = "") -> None:
    _inyectar(sandbox.payload_mensaje(telefono, texto, nombre))
