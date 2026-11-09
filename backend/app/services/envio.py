"""Reglas de envío. Aquí se aplican las políticas de WhatsApp antes de tocar la API:

1. Plantillas (mensajes iniciados por la empresa): solo a contactos con opt-in y solo
   plantillas aprobadas por Meta.
2. Texto libre: solo dentro de la ventana de atención de 24 h desde el último mensaje del cliente.
"""
from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Contacto, Mensaje, Plantilla, ahora
from app.services import plantillas as tpl
from app.whatsapp import rate_limit
from app.whatsapp.client import WhatsAppError, get_client

VENTANA_ATENCION = timedelta(hours=24)


class EnvioNoPermitido(Exception):
    pass


class ErrorReintentable(Exception):
    pass


def ventana_abierta(contacto: Contacto) -> bool:
    return bool(contacto.ultimo_entrante and ahora() - contacto.ultimo_entrante < VENTANA_ATENCION)


def preparar_plantilla(
    db: Session,
    contacto: Contacto,
    plantilla: Plantilla,
    variables: dict | None = None,
    *,
    origen: str,
    campana_id: int | None = None,
    disparador: str | None = None,
) -> Mensaje:
    """Crea el mensaje en estado `en_cola` (sin commit). Lanza EnvioNoPermitido si viola la política."""
    if not contacto.opt_in:
        raise EnvioNoPermitido("El contacto no tiene consentimiento (opt-in) vigente")
    if plantilla.estado != "APROBADA":
        raise EnvioNoPermitido(f"La plantilla '{plantilla.nombre}' no está aprobada por Meta")
    valores = {**tpl.variables_de_contacto(contacto), **(variables or {})}
    if faltan := tpl.faltantes(plantilla, valores):
        raise EnvioNoPermitido(f"Faltan valores para: {', '.join(faltan)}")

    usadas = tpl.extraer_variables(plantilla.encabezado, plantilla.cuerpo)
    mensaje = Mensaje(
        contacto=contacto,
        campana_id=campana_id,
        plantilla_id=plantilla.id,
        disparador=disparador,
        origen=origen,
        direccion="saliente",
        tipo="plantilla",
        contenido=tpl.texto_completo(plantilla, valores),
        variables={k: str(valores[k]) for k in usadas},
        estado="en_cola",
    )
    contacto.ultimo_mensaje = ahora()
    db.add(mensaje)
    return mensaje


def enviar_plantilla(db: Session, contacto, plantilla, variables=None, **kwargs) -> Mensaje:
    mensaje = preparar_plantilla(db, contacto, plantilla, variables, **kwargs)
    db.commit()
    encolar([mensaje.id])
    return mensaje


def enviar_texto(db: Session, contacto: Contacto, texto: str, origen: str = "manual") -> Mensaje:
    if not ventana_abierta(contacto):
        raise EnvioNoPermitido(
            "La ventana de 24 h está cerrada: el cliente no ha escrito en las últimas 24 horas. "
            "Usa una plantilla aprobada para retomar la conversación."
        )
    mensaje = Mensaje(
        contacto=contacto,
        origen=origen,
        direccion="saliente",
        tipo="texto",
        contenido=texto,
        estado="en_cola",
    )
    contacto.ultimo_mensaje = ahora()
    db.add(mensaje)
    db.commit()
    encolar([mensaje.id])
    return mensaje


def encolar(ids: list[int]) -> None:
    from app.tasks import enviar_mensaje  # import diferido: tasks importa este módulo

    for mensaje_id in ids:
        enviar_mensaje.delay(mensaje_id)


def ejecutar_envio(db: Session, mensaje_id: int) -> str:
    """Cuerpo de la tarea Celery. Idempotente: si el mensaje ya no está en cola, no hace nada."""
    # Reclamo atómico: si dos workers reciben la misma tarea, solo uno pasa de en_cola a enviando.
    reclamado = db.execute(
        update(Mensaje).where(Mensaje.id == mensaje_id, Mensaje.estado == "en_cola").values(estado="enviando")
    ).rowcount
    db.commit()
    if not reclamado:
        return "omitido"

    m = db.get(Mensaje, mensaje_id)
    contacto = m.contacto

    # Revalidar política en el momento del envío: el cliente pudo darse de baja mientras esperaba en cola.
    if m.tipo == "plantilla" and not contacto.opt_in:
        return _fallar(db, m, "El contacto se dio de baja antes del envío")
    if m.tipo == "texto" and not ventana_abierta(contacto):
        return _fallar(db, m, "Ventana de 24 h cerrada antes del envío")

    try:
        rate_limit.esperar_turno()
    except TimeoutError as exc:
        _devolver_a_cola(db, m)
        raise ErrorReintentable(str(exc)) from exc

    m.intentos += 1
    cliente = get_client()
    try:
        if m.tipo == "plantilla":
            p = db.get(Plantilla, m.plantilla_id)
            r = cliente.enviar_plantilla(contacto.telefono, p.nombre, p.idioma, tpl.componentes_envio(p, m.variables))
        else:
            r = cliente.enviar_texto(contacto.telefono, m.contenido)
    except WhatsAppError as exc:
        m.error, m.error_codigo = str(exc), exc.codigo
        if exc.reintentable and m.intentos < settings.max_reintentos:
            _devolver_a_cola(db, m)
            raise ErrorReintentable(str(exc)) from exc
        return _fallar(db, m, str(exc), exc.codigo)

    m.wamid = r.wamid
    m.estado = "aceptado"  # Meta lo aceptó; enviado/entregado/leído llegan por webhook
    m.enviado_en = ahora()
    m.error = None
    db.commit()

    if settings.sandbox:
        from app.tasks import simular_estados

        simular_estados.apply_async((m.id,), countdown=2)
    return "aceptado"


def _devolver_a_cola(db: Session, m: Mensaje) -> None:
    m.estado = "en_cola"
    db.commit()


def _fallar(db: Session, m: Mensaje, error: str, codigo: int | None = None) -> str:
    m.estado = "fallido"
    m.error = error
    m.error_codigo = codigo
    m.fallido_en = ahora()
    db.commit()
    return "fallido"
