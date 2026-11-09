"""Modelo de datos.

Convenciones:
- Teléfonos en formato E.164 sin "+", que es como los entrega la API de Meta (wa_id).
- Todas las fechas en UTC (timestamptz).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Contacto(Base):
    __tablename__ = "contactos"

    id: Mapped[int] = mapped_column(primary_key=True)
    telefono: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str | None] = mapped_column(String(160))
    etiquetas: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list, server_default="{}")

    # Estado vigente del consentimiento. El historial completo vive en `consentimientos`.
    opt_in: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    opt_in_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opt_in_origen: Mapped[str | None] = mapped_column(String(40))
    opt_out_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Ventana de atención de 24 h: solo se permite texto libre si el cliente escribió hace < 24 h.
    ultimo_entrante: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_mensaje: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    no_leidos: Mapped[int] = mapped_column(Integer, default=0)

    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    consentimientos: Mapped[list["Consentimiento"]] = relationship(
        back_populates="contacto", order_by="Consentimiento.fecha.desc()", cascade="all, delete-orphan"
    )


class Consentimiento(Base):
    """Registro inmutable (auditoría) de cada alta o baja de consentimiento."""

    __tablename__ = "consentimientos"

    id: Mapped[int] = mapped_column(primary_key=True)
    contacto_id: Mapped[int] = mapped_column(ForeignKey("contactos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # opt_in | opt_out
    origen: Mapped[str] = mapped_column(String(40))  # formulario_web, checkout, tienda, whatsapp, palabra_clave...
    detalle: Mapped[str | None] = mapped_column(Text)  # evidencia: texto aceptado, URL, id del mensaje...
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    contacto: Mapped[Contacto] = relationship(back_populates="consentimientos")


class Plantilla(Base):
    __tablename__ = "plantillas"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Meta exige minúsculas, números y guion bajo.
    nombre: Mapped[str] = mapped_column(String(512), unique=True)
    idioma: Mapped[str] = mapped_column(String(10), default="es")
    categoria: Mapped[str] = mapped_column(String(20), default="MARKETING")  # MARKETING | UTILITY
    encabezado: Mapped[str | None] = mapped_column(String(60))
    cuerpo: Mapped[str] = mapped_column(Text)
    pie: Mapped[str | None] = mapped_column(String(60))
    botones: Mapped[list[str]] = mapped_column(JSONB, default=list)  # respuestas rápidas
    ejemplos: Mapped[dict] = mapped_column(JSONB, default=dict)  # valor de ejemplo por variable (Meta lo pide)

    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")  # BORRADOR|PENDIENTE|APROBADA|RECHAZADA
    meta_id: Mapped[str | None] = mapped_column(String(64))
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)

    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=ahora)


class Campana(Base):
    __tablename__ = "campanas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    plantilla_id: Mapped[int] = mapped_column(ForeignKey("plantillas.id"))
    # {"etiquetas": ["vip"], "modo": "cualquiera" | "todas"}; sin etiquetas = todos los contactos con opt-in
    segmento: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Valores fijos para las variables que no salen del contacto, p. ej. {"producto": "...", "descuento": "20%"}
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR", index=True)
    # BORRADOR | PROGRAMADA | EN_CURSO | COMPLETADA | CANCELADA
    programada_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    iniciada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalizada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # NULL mientras el lanzamiento está creando los mensajes; así no se da por completada antes de tiempo.
    total_destinatarios: Mapped[int | None] = mapped_column(Integer)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plantilla: Mapped[Plantilla] = relationship()


class Mensaje(Base):
    __tablename__ = "mensajes"
    __table_args__ = (
        # Un contacto recibe una campaña una sola vez, aunque la tarea de lanzamiento se reintente.
        Index(
            "uq_mensaje_campana_contacto",
            "campana_id",
            "contacto_id",
            unique=True,
            postgresql_where="campana_id IS NOT NULL",
        ),
        Index("ix_mensajes_contacto_creado", "contacto_id", "creado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contacto_id: Mapped[int] = mapped_column(ForeignKey("contactos.id", ondelete="CASCADE"))
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id", ondelete="SET NULL"), index=True)
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas.id", ondelete="SET NULL"))
    disparador: Mapped[str | None] = mapped_column(String(30))  # bienvenida, carrito_abandonado, ...
    origen: Mapped[str] = mapped_column(String(20), default="campana")
    # campana | disparador | manual | auto_respuesta | sistema | cliente

    direccion: Mapped[str] = mapped_column(String(10))  # saliente | entrante
    tipo: Mapped[str] = mapped_column(String(20))  # plantilla | texto | boton
    contenido: Mapped[str] = mapped_column(Text)  # texto ya renderizado (lo que ve el cliente)
    variables: Mapped[dict] = mapped_column(JSONB, default=dict)

    wamid: Mapped[str | None] = mapped_column(String(128), unique=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    # salientes: en_cola → aceptado → enviado → entregado → leido | fallido ; entrantes: recibido
    error: Mapped[str | None] = mapped_column(Text)
    error_codigo: Mapped[int | None] = mapped_column(Integer)
    intentos: Mapped[int] = mapped_column(Integer, default=0)

    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entregado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    leido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fallido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    respondido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contacto: Mapped[Contacto] = relationship()


class EventoWebhook(Base):
    """Copia cruda de cada notificación recibida de Meta (o simulada en sandbox)."""

    __tablename__ = "eventos_webhook"

    id: Mapped[int] = mapped_column(primary_key=True)
    origen: Mapped[str] = mapped_column(String(10), default="meta")  # meta | sandbox
    tipo: Mapped[str] = mapped_column(String(30))  # status | message | template_status | otro
    wamid: Mapped[str | None] = mapped_column(String(128), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    firma_valida: Mapped[bool] = mapped_column(Boolean, default=True)
    procesado: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text)
    recibido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora, index=True)


class EventoNegocio(Base):
    """Eventos del e-commerce/CRM que alimentan los disparadores y la atribución de conversiones."""

    __tablename__ = "eventos_negocio"

    id: Mapped[int] = mapped_column(primary_key=True)
    contacto_id: Mapped[int] = mapped_column(ForeignKey("contactos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(30), index=True)
    # alta | carrito_abandonado | pago_pendiente | pago_realizado | compra
    referencia: Mapped[str | None] = mapped_column(String(80), index=True)  # id de carrito/pedido/factura
    datos: Mapped[dict] = mapped_column(JSONB, default=dict)  # producto, monto, vencimiento...
    monto: Mapped[float | None] = mapped_column(Numeric(12, 2))

    # Disparador asociado (si aplica)
    disparo_estado: Mapped[str] = mapped_column(String(15), default="no_aplica", index=True)
    # no_aplica | pendiente | enviado | cancelado | omitido
    disparo_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    disparo_detalle: Mapped[str | None] = mapped_column(Text)

    # Conversión atribuida (solo para compras)
    campana_id: Mapped[int | None] = mapped_column(ForeignKey("campanas.id", ondelete="SET NULL"), index=True)

    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    contacto: Mapped[Contacto] = relationship()


class Disparador(Base):
    __tablename__ = "disparadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), unique=True)
    # bienvenida | carrito_abandonado | recordatorio_pago | post_venta
    descripcion: Mapped[str] = mapped_column(String(200), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=False)
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas.id", ondelete="SET NULL"))
    retraso_minutos: Mapped[int] = mapped_column(Integer, default=0)

    plantilla: Mapped[Plantilla | None] = relationship()


class RespuestaAutomatica(Base):
    __tablename__ = "respuestas_automaticas"
    __table_args__ = (UniqueConstraint("nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    palabras_clave: Mapped[list[str]] = mapped_column(ARRAY(String(40)))
    respuesta: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    coincidencias: Mapped[int] = mapped_column(Integer, default=0)
