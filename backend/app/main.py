import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api import automatizaciones, campanas, contactos, conversaciones, dashboard, eventos, plantillas, sistema, webhook
from app.api.deps import usuario_actual
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea = None
    if settings.celery_eager:
        # Sin worker ni beat: la API ejecuta ella misma la tarea periódica (solo para demos).
        from app.tasks import procesar_programados

        async def bucle():
            while True:
                await asyncio.sleep(30)
                try:
                    await run_in_threadpool(procesar_programados)
                except Exception:
                    logging.exception("procesar_programados falló")

        tarea = asyncio.create_task(bucle())
    yield
    if tarea:
        tarea.cancel()


app = FastAPI(
    title="WhatsApp Ventas",
    description="Automatización de mensajes de ventas sobre la WhatsApp Business Cloud API oficial de Meta.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

protegido = [Depends(usuario_actual)]
app.include_router(webhook.router)  # público, protegido por firma HMAC
app.include_router(sistema.router)  # login público; el resto declara su dependencia
app.include_router(eventos.router)  # API key de integración o token del panel
for modulo in (contactos, plantillas, campanas, conversaciones, automatizaciones, dashboard):
    app.include_router(modulo.router, dependencies=protegido)


@app.get("/salud")
def salud():
    return {"ok": True, "modo": "sandbox" if settings.sandbox else "cloud"}
