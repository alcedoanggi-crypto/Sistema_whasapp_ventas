import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.plantillas import PATRON_NOMBRE_PLANTILLA


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def normalizar_telefono(valor: str) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    if not 8 <= len(digitos) <= 15:
        raise ValueError("Teléfono inválido: usa formato internacional, p. ej. 584121234567")
    return digitos


# ------------------------------------------------------------ contactos
class ConsentimientoOut(ORM):
    id: int
    tipo: str
    origen: str
    detalle: str | None
    fecha: datetime


class ContactoOut(ORM):
    id: int
    telefono: str
    nombre: str
    email: str | None
    etiquetas: list[str]
    opt_in: bool
    opt_in_fecha: datetime | None
    opt_in_origen: str | None
    opt_out_fecha: datetime | None
    ultimo_entrante: datetime | None
    ultimo_mensaje: datetime | None
    no_leidos: int
    creado: datetime


class ContactoIn(BaseModel):
    telefono: str
    nombre: str = ""
    email: str | None = None
    etiquetas: list[str] = []
    # Consentimiento: obligatorio declarar el origen si se marca opt-in
    opt_in: bool = False
    origen_consentimiento: str | None = None
    evidencia: str | None = None

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v):
        return normalizar_telefono(v)

    @field_validator("etiquetas")
    @classmethod
    def _etiquetas(cls, v):
        return sorted({e.strip().lower() for e in v if e.strip()})


class ContactoUpdate(BaseModel):
    nombre: str | None = None
    email: str | None = None
    etiquetas: list[str] | None = None


class CambioConsentimiento(BaseModel):
    opt_in: bool
    origen: str = "manual"
    evidencia: str | None = None


# ------------------------------------------------------------ plantillas
class PlantillaIn(BaseModel):
    nombre: str
    idioma: str = "es"
    categoria: str = "MARKETING"
    encabezado: str | None = None
    cuerpo: str = Field(min_length=1, max_length=1024)
    pie: str | None = None
    botones: list[str] = Field(default_factory=list, max_length=3)
    ejemplos: dict[str, str] = {}

    @field_validator("nombre")
    @classmethod
    def _nombre(cls, v):
        v = v.strip().lower().replace(" ", "_")
        if not PATRON_NOMBRE_PLANTILLA.match(v):
            raise ValueError("Solo minúsculas, números y guion bajo")
        return v

    @field_validator("categoria")
    @classmethod
    def _cat(cls, v):
        if v not in ("MARKETING", "UTILITY"):
            raise ValueError("Categoría MARKETING o UTILITY")
        return v


class PlantillaOut(ORM):
    id: int
    nombre: str
    idioma: str
    categoria: str
    encabezado: str | None
    cuerpo: str
    pie: str | None
    botones: list[str]
    ejemplos: dict
    estado: str
    meta_id: str | None
    motivo_rechazo: str | None
    variables: list[str] = []
    actualizado: datetime


# ------------------------------------------------------------ campañas
class Segmento(BaseModel):
    etiquetas: list[str] = []
    modo: str = "cualquiera"  # cualquiera | todas


class CampanaIn(BaseModel):
    nombre: str = Field(min_length=1)
    plantilla_id: int
    segmento: Segmento = Segmento()
    variables: dict[str, str] = {}
    programada_para: datetime | None = None  # None = queda en borrador


class CampanaOut(ORM):
    id: int
    nombre: str
    plantilla_id: int
    segmento: dict
    variables: dict
    estado: str
    programada_para: datetime | None
    iniciada: datetime | None
    finalizada: datetime | None
    total_destinatarios: int | None
    creado: datetime


# ------------------------------------------------------------ mensajes
class MensajeOut(ORM):
    id: int
    contacto_id: int
    campana_id: int | None
    disparador: str | None
    origen: str
    direccion: str
    tipo: str
    contenido: str
    estado: str
    error: str | None
    intentos: int
    creado: datetime
    enviado_en: datetime | None
    entregado_en: datetime | None
    leido_en: datetime | None


class TextoIn(BaseModel):
    texto: str = Field(min_length=1, max_length=4096)


class PlantillaEnvioIn(BaseModel):
    plantilla_id: int
    variables: dict[str, str] = {}


# ------------------------------------------------------------ automatizaciones
class DisparadorIn(BaseModel):
    activo: bool
    plantilla_id: int | None = None
    retraso_minutos: int = Field(ge=0, le=60 * 24 * 30)


class DisparadorOut(ORM):
    id: int
    tipo: str
    descripcion: str
    activo: bool
    plantilla_id: int | None
    retraso_minutos: int


class RespuestaIn(BaseModel):
    nombre: str
    palabras_clave: list[str] = Field(min_length=1)
    respuesta: str = Field(min_length=1, max_length=4096)
    activo: bool = True
    prioridad: int = 0


class RespuestaOut(ORM):
    id: int
    nombre: str
    palabras_clave: list[str]
    respuesta: str
    activo: bool
    prioridad: int
    coincidencias: int


# ------------------------------------------------------------ eventos de negocio
class EventoIn(BaseModel):
    telefono: str
    tipo: str
    referencia: str | None = None
    datos: dict = {}
    monto: float | None = None
    nombre: str | None = None

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v):
        return normalizar_telefono(v)


class EventoOut(ORM):
    id: int
    contacto_id: int
    tipo: str
    referencia: str | None
    datos: dict
    monto: float | None
    disparo_estado: str
    disparo_en: datetime | None
    disparo_detalle: str | None
    campana_id: int | None
    creado: datetime
