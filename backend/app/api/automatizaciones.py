from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Disparador, Plantilla, RespuestaAutomatica
from app.schemas import DisparadorIn, DisparadorOut, RespuestaIn, RespuestaOut
from app.services.webhook import PALABRAS_ALTA, PALABRAS_BAJA, buscar_respuesta_automatica, normalizar

router = APIRouter(prefix="/api/automatizaciones", tags=["automatizaciones"])


@router.get("/disparadores", response_model=list[DisparadorOut])
def disparadores(db: Session = Depends(get_db)):
    return db.scalars(select(Disparador).order_by(Disparador.id)).all()


@router.put("/disparadores/{disparador_id}", response_model=DisparadorOut)
def actualizar_disparador(disparador_id: int, datos: DisparadorIn, db: Session = Depends(get_db)):
    d = db.get(Disparador, disparador_id)
    if d is None:
        raise HTTPException(404, "Disparador no encontrado")
    if datos.activo:
        p = db.get(Plantilla, datos.plantilla_id) if datos.plantilla_id else None
        if p is None or p.estado != "APROBADA":
            raise HTTPException(422, "Para activarlo elige una plantilla aprobada")
    d.activo, d.plantilla_id, d.retraso_minutos = datos.activo, datos.plantilla_id, datos.retraso_minutos
    db.commit()
    return d


@router.get("/respuestas", response_model=list[RespuestaOut])
def respuestas(db: Session = Depends(get_db)):
    return db.scalars(
        select(RespuestaAutomatica).order_by(RespuestaAutomatica.prioridad.desc(), RespuestaAutomatica.id)
    ).all()


@router.post("/respuestas", response_model=RespuestaOut, status_code=201)
def crear_respuesta(datos: RespuestaIn, db: Session = Depends(get_db)):
    _validar_palabras(datos.palabras_clave)
    r = RespuestaAutomatica(**datos.model_dump())
    db.add(r)
    db.commit()
    return r


@router.put("/respuestas/{respuesta_id}", response_model=RespuestaOut)
def actualizar_respuesta(respuesta_id: int, datos: RespuestaIn, db: Session = Depends(get_db)):
    r = db.get(RespuestaAutomatica, respuesta_id)
    if r is None:
        raise HTTPException(404, "Respuesta no encontrada")
    _validar_palabras(datos.palabras_clave)
    for campo, valor in datos.model_dump().items():
        setattr(r, campo, valor)
    db.commit()
    return r


@router.delete("/respuestas/{respuesta_id}", status_code=204)
def eliminar_respuesta(respuesta_id: int, db: Session = Depends(get_db)):
    r = db.get(RespuestaAutomatica, respuesta_id)
    if r:
        db.delete(r)
        db.commit()


@router.post("/respuestas/probar")
def probar(texto: dict, db: Session = Depends(get_db)):
    """Qué contestaría el bot ante un mensaje, sin enviar nada."""
    comando = normalizar(texto.get("texto", ""))
    if comando in PALABRAS_BAJA:
        return {"accion": "baja"}
    if comando in PALABRAS_ALTA:
        return {"accion": "alta"}
    regla = buscar_respuesta_automatica(db, comando)
    return {"accion": "respuesta" if regla else "ninguna", "regla": RespuestaOut.model_validate(regla) if regla else None}


def _validar_palabras(palabras: list[str]) -> None:
    reservadas = {normalizar(p) for p in palabras} & (PALABRAS_BAJA | PALABRAS_ALTA)
    if reservadas:
        raise HTTPException(422, f"Palabras reservadas para alta/baja: {', '.join(sorted(reservadas))}")
