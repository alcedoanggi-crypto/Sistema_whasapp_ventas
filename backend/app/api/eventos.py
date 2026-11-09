"""Entrada para el e-commerce/CRM: carritos abandonados, pagos pendientes y compras.

Ejemplo desde la tienda:
    curl -X POST http://localhost:5059/api/eventos -H "X-API-Key: ..." -H "Content-Type: application/json" \
         -d '{"telefono":"584121234567","tipo":"carrito_abandonado","referencia":"cart-991",
              "datos":{"producto":"Zapatillas Run X"}}'
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import integracion_o_usuario, usuario_actual
from app.db import get_db
from app.models import Contacto, EventoNegocio
from app.schemas import EventoIn, EventoOut
from app.services import disparadores

router = APIRouter(prefix="/api/eventos", tags=["eventos"])


@router.post("", response_model=EventoOut, status_code=201, dependencies=[Depends(integracion_o_usuario)])
def registrar(datos: EventoIn, db: Session = Depends(get_db)):
    contacto = db.scalar(select(Contacto).where(Contacto.telefono == datos.telefono))
    if contacto is None:
        # El evento se guarda (sirve para métricas), pero sin opt-in el disparador lo omitirá.
        contacto = Contacto(telefono=datos.telefono, nombre=datos.nombre or "", etiquetas=[])
        db.add(contacto)
        db.flush()
    try:
        return disparadores.registrar_evento(db, contacto, datos.tipo, datos.referencia, datos.datos, datos.monto)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@router.get("", response_model=list[EventoOut], dependencies=[Depends(usuario_actual)])
def listar(tipo: str | None = None, limite: int = Query(100, le=500), db: Session = Depends(get_db)):
    q = select(EventoNegocio).order_by(EventoNegocio.creado.desc()).limit(limite)
    if tipo:
        q = q.where(EventoNegocio.tipo == tipo)
    return db.scalars(q).all()
