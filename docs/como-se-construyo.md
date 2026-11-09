# Cómo se construyó WhatsApp Ventas

Este documento cuenta el proceso de desarrollo del proyecto: qué problema resuelve, qué decisiones técnicas se tomaron y por qué, en qué orden se construyó y qué problemas aparecieron por el camino.

---

## 1. El problema

Una tienda online vende por WhatsApp, pero los mensajes se mandan a mano: promociones a toda la lista, recordatorios de pago olvidados, carritos abandonados que nadie sigue. Eso tiene tres riesgos:

- **Bloqueo del número:** WhatsApp suspende a quien envía mensajes no deseados, sin consentimiento o desde herramientas no oficiales.
- **Oportunidades perdidas:** sin automatización, el carrito abandonado o el pago pendiente se olvidan.
- **Sin métricas:** no se sabe qué campaña vende y cuál solo molesta.

**Objetivo:** un panel que automatice los mensajes de venta **cumpliendo las políticas de WhatsApp Business** y que mida resultados de punta a punta, desde el envío hasta la venta atribuida.

## 2. Requisitos que guiaron el diseño

1. Solo la **API oficial** (WhatsApp Business Cloud API de Meta). Nada de librerías que simulan WhatsApp Web, que violan los términos y terminan en bloqueo.
2. **Consentimiento auditable:** nadie recibe mensajes sin opt-in, y cada alta o baja queda registrada con fecha, origen y evidencia.
3. **Plantillas aprobadas** para iniciar conversaciones y **ventana de 24 h** para texto libre, como exige Meta.
4. **Envíos masivos confiables:** límite de velocidad, reintentos y cero duplicados aunque un proceso se caiga.
5. **Demostrable sin cuenta de Meta:** cualquiera que clone el repositorio debe poder ver el sistema funcionando.

## 3. Decisiones técnicas

| Decisión | Alternativa descartada | Por qué |
|---|---|---|
| **FastAPI** + Pydantic | Flask | Validación de datos declarativa, documentación OpenAPI automática en `/docs` y buen rendimiento para el webhook. |
| **PostgreSQL** + SQLAlchemy 2 + Alembic | SQLite | Concurrencia real entre la API y varios workers, `JSONB` para guardar los payloads de Meta y migraciones versionadas. |
| **Celery + Redis** para los envíos | Enviar dentro de la petición HTTP | Una campaña a miles de contactos no puede bloquear la API; los envíos necesitan cola, reintentos y control de velocidad. |
| **Celery Beat cada 30 s** + fechas en PostgreSQL | `countdown` largos de Celery | Un post-venta a 3 días no debe depender de que una tarea sobreviva días en Redis. La fecha vive en la base de datos y Beat recoge lo vencido. |
| **Modo sandbox** con payloads idénticos a los de Meta | Datos falsos solo en el frontend | El sandbox genera notificaciones con la misma forma que el webhook real y las procesa **el mismo código de producción**. La demo prueba el sistema de verdad. |
| **React + Vite + Tailwind + Recharts** | Plantillas del servidor | Panel interactivo (vista previa de plantillas en un teléfono, bandeja tipo chat, gráficos) con recarga rápida en desarrollo. |

## 4. Arquitectura

```
React (5174) ──/api──► FastAPI (5059) ◄── webhook de Meta (firma HMAC)
                          │       │
                    PostgreSQL   Redis ──► Celery worker ──► Graph API de Meta
                          ▲                   + Beat (30 s)
                          └───────────────────────┘
```

- La **API** valida, guarda y encola; nunca llama a Meta dentro de una petición del usuario.
- El **webhook** solo verifica la firma, guarda el payload crudo en `eventos_webhook` y encola su procesamiento. Así responde a Meta en milisegundos.
- El **worker** envía los mensajes, procesa estados (enviado → entregado → leído) y ejecuta disparadores y respuestas automáticas.
- **Beat** lanza campañas programadas, disparadores con retraso y rescata mensajes atascados.

## 5. Orden de construcción

1. **Modelo de datos y migración inicial:** `contactos`, `consentimientos` (registro inmutable), `plantillas`, `campanas`, `mensajes`, `eventos_webhook`, `eventos_negocio`, `disparadores` y `respuestas_automaticas`.
2. **Cliente de WhatsApp con dos implementaciones** que comparten interfaz: el real (Graph API v21.0) y el sandbox. Se elige con `WHATSAPP_MODE`, y el resto del código no sabe cuál está usando.
3. **Servicio de envío con las políticas:** verifica opt-in vigente, plantilla aprobada y ventana de 24 h antes de crear cualquier mensaje.
4. **Tareas de Celery:** envío con reintentos, procesamiento del webhook, lanzamiento de campañas, disparadores y tarea periódica.
5. **Webhook:** verificación `GET` con el token y `POST` con firma `X-Hub-Signature-256`.
6. **Automatizaciones:** disparadores por eventos de la tienda (bienvenida, carrito abandonado, recordatorio de pago, post-venta) y respuestas por palabra clave con prioridad.
7. **Atribución de ventas:** una compra dentro de los 7 días siguientes a un mensaje de campaña se atribuye a esa campaña.
8. **Frontend:** dashboard, bandeja de conversaciones, editor de plantillas con vista previa, campañas, contactos, automatizaciones y vista del sistema.
9. **Datos de demostración y pruebas.**
10. **Documentación:** README, guía de Meta y este documento.

## 6. Problemas resueltos

### Envíos duplicados
Si un worker se cae después de enviar pero antes de confirmar, Celery reentrega la tarea (`acks_late=True`) y el cliente recibiría el mensaje dos veces.
**Solución:** cada mensaje se *reclama* con un `UPDATE mensajes SET estado='enviando' WHERE id=… AND estado='en_cola'` atómico. Solo un worker puede ganar ese cambio; los demás ven 0 filas afectadas y no envían.

### Límite de velocidad compartido
Meta limita los mensajes por segundo. Con varios workers en paralelo, un contador en memoria no sirve.
**Solución:** limitador de ventana fija en Redis (`INCR` + `EXPIRE` por segundo) compartido por todos los workers, más **backoff exponencial con jitter** ante errores 429, 5xx y los códigos de límite de Meta (130429, 131056).

### Estados que llegan antes que el envío
A veces Meta notifica «entregado» antes de que el worker haya guardado el `wamid` del mensaje.
**Solución:** si el procesamiento del webhook no encuentra el `wamid`, la tarea se **reintenta** con espera en lugar de descartar el evento.

### Seguridad del webhook
Cualquiera podría enviar un POST falso al webhook.
**Solución:** se recalcula el HMAC-SHA256 del **cuerpo crudo** con el App Secret y se compara en tiempo constante con la cabecera de Meta. Lo que no coincide se rechaza con 401.

### Redis compartido con otro proyecto
En la misma máquina corría otro proyecto con Celery en la misma instancia de Redis, y su worker llegó a tomar tareas que no eran suyas.
**Solución:** base de Redis propia (`/3`) y cola propia (`whatsapp_ventas`), así los proyectos quedan aislados.

### Celery en Windows
El pool por defecto de Celery (`prefork`) no funciona en Windows.
**Solución:** worker con `--pool=threads`; además, `CELERY_EAGER=true` permite una demo sin Redis ni worker.

## 7. Pruebas

`pytest` cubre la lógica crítica: verificación de la firma del webhook, extracción y renderizado de variables de plantillas, detección de palabras de baja (BAJA, STOP, DETENER…), normalización de teléfonos y autenticación. El modo sandbox sirve además como prueba de integración de todo el flujo: campaña, estados, lectura, respuesta del cliente, respuesta automática y atribución de la venta.

## 8. Qué aprendí

- Integrar una **API de terceros con reglas estrictas** (plantillas, ventanas, límites) y convertir esas reglas en validaciones del propio sistema.
- Diseñar **procesamiento asíncrono confiable**: idempotencia, reintentos con backoff y tareas programadas que sobreviven a reinicios.
- Tratar el **consentimiento como dato de primera clase**, con historial inmutable y auditable.
- Construir un **modo demo que ejecuta el código real**, en lugar de una maqueta.

## 9. Siguientes pasos

- Plantillas con imagen o documento en el encabezado.
- Varios usuarios con roles (administrador, agente de ventas).
- Pruebas A/B entre dos plantillas de una misma campaña.
- Despliegue en la nube con HTTPS propio para el webhook.
