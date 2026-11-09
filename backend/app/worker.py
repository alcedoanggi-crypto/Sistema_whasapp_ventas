"""Aplicación Celery.

Windows:  celery -A app.worker worker --pool=threads --concurrency=8 -l info
          celery -A app.worker beat -l info
Linux:    celery -A app.worker worker -B --concurrency=8 -l info
"""
from celery import Celery

from app.config import settings

celery = Celery("whatsapp_ventas", broker=settings.redis_url, include=["app.tasks"])
celery.conf.update(
    task_always_eager=settings.celery_eager,
    task_eager_propagates=False,
    task_acks_late=True,  # si el worker muere a mitad de tarea, otra la retoma
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    timezone="UTC",
    # Cola propia: si otro proyecto comparte el Redis, ni robamos sus tareas ni él las nuestras.
    task_default_queue="whatsapp_ventas",
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "procesar-programados": {"task": "app.tasks.procesar_programados", "schedule": 30.0},
    },
)
