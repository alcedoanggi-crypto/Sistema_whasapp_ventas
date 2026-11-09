"""Alta y baja de consentimiento. Cada cambio deja un registro inmutable en `consentimientos`."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Consentimiento, Contacto, ahora

ORIGENES = {
    "formulario_web": "Formulario web",
    "checkout": "Checkout de la tienda",
    "tienda_fisica": "Tienda física",
    "whatsapp": "Escribió ALTA por WhatsApp",
    "importacion": "Importación con evidencia",
    "palabra_clave": "Respondió una palabra de baja",
    "manual": "Cambio manual en el panel",
}


def registrar_opt_in(
    db: Session, contacto: Contacto, origen: str, detalle: str | None = None, fecha: datetime | None = None
) -> Consentimiento:
    fecha = fecha or ahora()
    contacto.opt_in = True
    contacto.opt_in_fecha = fecha
    contacto.opt_in_origen = origen
    contacto.opt_out_fecha = None
    registro = Consentimiento(contacto=contacto, tipo="opt_in", origen=origen, detalle=detalle, fecha=fecha)
    db.add(registro)
    return registro


def registrar_opt_out(
    db: Session, contacto: Contacto, origen: str, detalle: str | None = None, fecha: datetime | None = None
) -> Consentimiento:
    fecha = fecha or ahora()
    contacto.opt_in = False
    contacto.opt_out_fecha = fecha
    registro = Consentimiento(contacto=contacto, tipo="opt_out", origen=origen, detalle=detalle, fecha=fecha)
    db.add(registro)
    return registro
