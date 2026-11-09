from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Contacto, EventoNegocio
from app.schemas import (
    CambioConsentimiento,
    ConsentimientoOut,
    ContactoIn,
    ContactoOut,
    ContactoUpdate,
    EventoOut,
)
from app.services import consentimientos, disparadores
from app.services.consentimientos import ORIGENES

router = APIRouter(prefix="/api/contactos", tags=["contactos"])


@router.get("")
def listar(
    q: str | None = None,
    etiqueta: str | None = None,
    opt_in: bool | None = None,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(25, ge=1, le=200),
    db: Session = Depends(get_db),
):
    consulta = select(Contacto)
    if q:
        like = f"%{q}%"
        consulta = consulta.where(or_(Contacto.nombre.ilike(like), Contacto.telefono.like(like), Contacto.email.ilike(like)))
    if etiqueta:
        consulta = consulta.where(Contacto.etiquetas.any(etiqueta))
    if opt_in is not None:
        consulta = consulta.where(Contacto.opt_in.is_(opt_in))
    total = db.scalar(select(func.count()).select_from(consulta.subquery()))
    filas = db.scalars(consulta.order_by(Contacto.creado.desc()).offset((pagina - 1) * por_pagina).limit(por_pagina))
    return {"total": total, "items": [ContactoOut.model_validate(c) for c in filas]}


@router.get("/etiquetas")
def etiquetas(db: Session = Depends(get_db)):
    filas = db.execute(
        select(func.unnest(Contacto.etiquetas).label("e"), func.count()).group_by("e").order_by("e")
    ).all()
    return [{"etiqueta": e, "contactos": n} for e, n in filas]


@router.get("/origenes")
def origenes():
    return ORIGENES


@router.post("", response_model=ContactoOut, status_code=201)
def crear(datos: ContactoIn, db: Session = Depends(get_db)):
    if db.scalar(select(Contacto.id).where(Contacto.telefono == datos.telefono)):
        raise HTTPException(409, "Ya existe un contacto con ese teléfono")
    if datos.opt_in and not datos.origen_consentimiento:
        raise HTTPException(422, "Indica el origen del consentimiento (dónde y cómo aceptó recibir mensajes)")
    contacto = Contacto(telefono=datos.telefono, nombre=datos.nombre, email=datos.email, etiquetas=datos.etiquetas)
    db.add(contacto)
    if datos.opt_in:
        consentimientos.registrar_opt_in(db, contacto, datos.origen_consentimiento, datos.evidencia)
    db.commit()
    if datos.opt_in:
        disparadores.registrar_evento(db, contacto, "alta")  # mensaje de bienvenida
    return contacto


@router.get("/{contacto_id}")
def detalle(contacto_id: int, db: Session = Depends(get_db)):
    c = _obtener(db, contacto_id)
    eventos = db.scalars(
        select(EventoNegocio).where(EventoNegocio.contacto_id == c.id).order_by(EventoNegocio.creado.desc()).limit(50)
    )
    return {
        "contacto": ContactoOut.model_validate(c),
        "consentimientos": [ConsentimientoOut.model_validate(x) for x in c.consentimientos],
        "eventos": [EventoOut.model_validate(e) for e in eventos],
    }


@router.patch("/{contacto_id}", response_model=ContactoOut)
def actualizar(contacto_id: int, datos: ContactoUpdate, db: Session = Depends(get_db)):
    c = _obtener(db, contacto_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if campo == "etiquetas":
            valor = sorted({e.strip().lower() for e in valor if e.strip()})
        setattr(c, campo, valor)
    db.commit()
    return c


@router.post("/{contacto_id}/consentimiento", response_model=ContactoOut)
def cambiar_consentimiento(contacto_id: int, datos: CambioConsentimiento, db: Session = Depends(get_db)):
    c = _obtener(db, contacto_id)
    if datos.opt_in == c.opt_in:
        return c
    if datos.opt_in:
        consentimientos.registrar_opt_in(db, c, datos.origen, datos.evidencia)
    else:
        consentimientos.registrar_opt_out(db, c, datos.origen, datos.evidencia)
    db.commit()
    return c


@router.delete("/{contacto_id}", status_code=204)
def eliminar(contacto_id: int, db: Session = Depends(get_db)):
    db.delete(_obtener(db, contacto_id))
    db.commit()


def _obtener(db: Session, contacto_id: int) -> Contacto:
    c = db.get(Contacto, contacto_id)
    if c is None:
        raise HTTPException(404, "Contacto no encontrado")
    return c
