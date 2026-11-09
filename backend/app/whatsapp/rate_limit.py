"""Límite de velocidad global: todos los workers comparten el contador en Redis.

Ventana fija de 1 segundo. Basta para respetar el throughput por número de la Cloud API
(80 msg/s por defecto) independientemente de cuántos workers haya levantados.
"""
import threading
import time

import redis

from app.config import settings

_cliente: redis.Redis | None = None
_sin_redis = False
_lock = threading.Lock()
_local = {"segundo": 0, "cuenta": 0}


def _redis() -> redis.Redis | None:
    global _cliente, _sin_redis
    if _cliente is None and not _sin_redis:
        try:
            _cliente = redis.Redis.from_url(settings.redis_url, socket_timeout=2)
            _cliente.ping()
        except redis.RedisError:
            _cliente, _sin_redis = None, True
    return _cliente


def _intentar(clave: str, limite: int) -> bool:
    segundo = int(time.time())
    r = _redis()
    if r is not None:
        k = f"wa:rl:{clave}:{segundo}"
        pipe = r.pipeline()
        pipe.incr(k)
        pipe.expire(k, 2)
        cuenta, _ = pipe.execute()
        return cuenta <= limite
    # Sin Redis (modo demo CELERY_EAGER): limitador en memoria del proceso.
    with _lock:
        if _local["segundo"] != segundo:
            _local.update(segundo=segundo, cuenta=0)
        _local["cuenta"] += 1
        return _local["cuenta"] <= limite


def esperar_turno(clave: str = "global", limite: int | None = None, max_espera: float = 30.0) -> None:
    limite = limite or settings.rate_limit_mps
    inicio = time.monotonic()
    while not _intentar(clave, limite):
        if time.monotonic() - inicio > max_espera:
            raise TimeoutError("Límite de velocidad saturado")
        time.sleep(1 - (time.time() % 1) + 0.01)  # dormir hasta el siguiente segundo
