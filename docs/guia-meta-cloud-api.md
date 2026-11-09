# Guía: cuenta de desarrollador de Meta y token de prueba

Esta guía lleva el proyecto de **modo sandbox** (simulado) a **modo cloud** (WhatsApp Business Cloud API oficial). Necesitas unos 20 minutos y una cuenta personal de Facebook.

> La interfaz de Meta cambia con frecuencia: los nombres de menú pueden variar un poco, pero el flujo es siempre el mismo.

---

## 1. Crear la cuenta de desarrollador

1. Entra a **https://developers.facebook.com** e inicia sesión con tu cuenta de Facebook.
2. Pulsa **Comenzar / Get Started**, acepta los términos de la plataforma y verifica tu cuenta (teléfono o correo).
3. Elige el rol **Desarrollador**.

## 2. Crear la app

1. **Mis apps → Crear app**.
2. Caso de uso: **Otro → Empresa (Business)**. (En la versión nueva del asistente: *"Conectar con clientes a través de WhatsApp"*).
3. Ponle nombre (p. ej. `whatsapp-ventas-demo`) y un correo de contacto.
4. Si te pide un **portafolio comercial (Business Manager)**, crea uno nuevo; Meta lo usa para colgar la cuenta de WhatsApp Business (WABA).
5. En el panel de la app, en **Agregar productos**, pulsa **Configurar** en **WhatsApp**.

Meta crea automáticamente:

- una **WhatsApp Business Account (WABA) de prueba**,
- un **número de teléfono de prueba** (de EE. UU., +1 555…), gratis,
- un **token de acceso temporal** (24 h).

## 3. Obtener los datos para el `.env`

Ve a **WhatsApp → Configuración de la API (API Setup)**:

| Dato en Meta | Variable en `backend/.env` |
|---|---|
| **Token de acceso temporal** (botón *Generar*) | `WHATSAPP_TOKEN` |
| **Identificador del número de teléfono** (Phone number ID) | `WHATSAPP_PHONE_NUMBER_ID` |
| **Identificador de la cuenta de WhatsApp Business** (WABA ID) | `WHATSAPP_BUSINESS_ACCOUNT_ID` |

Y en **Configuración de la app → Básica**:

| Dato | Variable |
|---|---|
| **Clave secreta de la app** (App Secret, botón *Mostrar*) | `WHATSAPP_APP_SECRET` |

Después cambia `WHATSAPP_MODE=cloud` y reinicia API y worker.

## 4. Registrar destinatarios de prueba

Con el número de prueba **solo puedes escribir a un máximo de 5 números verificados**:

1. En **API Setup → Para (To)**, pulsa **Administrar lista de números**.
2. Agrega tu WhatsApp personal; te llegará un código de verificación.
3. Da de alta ese mismo número como contacto en el panel (con opt-in y su origen) para poder enviarle campañas.

Prueba rápida desde la terminal (la plantilla `hello_world` viene aprobada por defecto):

```bash
curl -X POST "https://graph.facebook.com/v21.0/$WHATSAPP_PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer $WHATSAPP_TOKEN" -H "Content-Type: application/json" \
  -d '{"messaging_product":"whatsapp","to":"584121234567","type":"template",
       "template":{"name":"hello_world","language":{"code":"en_US"}}}'
```

## 5. Configurar el webhook

Meta necesita una URL **HTTPS pública**. En desarrollo:

```bash
ngrok http 5059          # o: cloudflared tunnel --url http://localhost:5059
```

En **WhatsApp → Configuración → Webhook → Editar**:

- **URL de devolución de llamada:** `https://<tu-subdominio>.ngrok-free.app/webhook`
- **Token de verificación:** el valor de `WHATSAPP_VERIFY_TOKEN` (texto libre que tú eliges).

Al guardar, Meta hace un `GET /webhook?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…`; la app responde el `challenge` si el token coincide.

Luego, en **Campos del webhook**, suscríbete a:

- `messages` → estados (sent, delivered, read, failed) y mensajes entrantes de clientes.
- `message_template_status_update` → aprobación o rechazo de plantillas.

Cada `POST` de Meta trae la cabecera `X-Hub-Signature-256: sha256=<HMAC>`; el backend recalcula el HMAC‑SHA256 del cuerpo crudo con el App Secret y rechaza con **401** lo que no coincida.

## 6. Plantillas

Desde el panel (**Plantillas → Enviar a revisión de Meta**) la app llama a `POST /{WABA_ID}/message_templates` usando **parámetros con nombre** (`{{nombre}}`, `{{producto}}`…) y los valores de ejemplo que exige Meta. La revisión suele tardar entre minutos y unas horas; el resultado llega por webhook y también puede consultarse con **Consultar estado en Meta**.

Reglas que conviene respetar para que la aprueben:

- **MARKETING** para promociones, **UTILITY** solo para mensajes transaccionales (pago, pedido).
- No empezar ni terminar el cuerpo con una variable, y no poner variables seguidas.
- Incluir cómo darse de baja en las de marketing (el pie *"Responde BAJA…"*).

## 7. Token permanente (para producción)

El token temporal caduca a las 24 h. Para uno permanente:

1. **business.facebook.com → Configuración del negocio → Usuarios → Usuarios del sistema → Agregar** (rol Administrador).
2. **Asignar activos**: tu app (control total) y tu WABA.
3. **Generar token** → selecciona la app y los permisos `whatsapp_business_messaging` y `whatsapp_business_management`, caducidad *Nunca*.
4. Pega el token en `WHATSAPP_TOKEN`. Guárdalo como secreto: nunca en el repositorio.

## 8. Pasar a un número real

En **API Setup → Agregar número de teléfono**: un número que **no** esté registrado en la app de WhatsApp (o elimínalo de ella antes), nombre visible aprobado por Meta y verificación del negocio para subir los límites de mensajería (empiezan en 250 conversaciones iniciadas por el negocio cada 24 h).

## 9. Tu primer mensaje real desde el panel (paso a paso)

Con los pasos 1 a 4 hechos (app creada, tu número verificado como destinatario y el `.env` completo):

1. **Activa el modo real** en `backend/.env` y reinicia la API y el worker:
   ```ini
   WHATSAPP_MODE=cloud
   WHATSAPP_TOKEN=EAAG...                 # token temporal o permanente
   WHATSAPP_PHONE_NUMBER_ID=1234567890
   WHATSAPP_BUSINESS_ACCOUNT_ID=9876543210
   ```
   El aviso amarillo «MODO SIMULACIÓN» desaparece del panel y **Webhook y sistema** muestra *Modo: cloud* y *Token configurado: sí*.
2. **Contacto:** en **Contactos → Nuevo contacto** registra tu número con código de país y sin `+` ni espacios (p. ej. `584241234567`), con **opt-in** y su origen, y ponle una etiqueta, por ejemplo `prueba`.
3. **Plantilla `hello_world`:** Meta la trae aprobada en toda cuenta nueva. En **Plantillas → Nueva** crea una con nombre `hello_world`, idioma **Inglés (en_US)**, categoría *UTILITY* y cuerpo `Welcome and congratulations!!`. Guárdala y pulsa **Consultar estado en Meta**: pasará a **APROBADA** porque ya existe en tu cuenta.
4. **Campaña:** en **Campañas → Nueva** elige la plantilla `hello_world`, el segmento con la etiqueta `prueba` y pulsa **Lanzar**.
5. En segundos te llega el mensaje *Hello World* a tu WhatsApp. En el detalle de la campaña el mensaje pasa a **enviado**.

> **Estados entregado/leído y respuestas:** Meta los informa por webhook. Sin el paso 5 (ngrok + webhook) el mensaje sí llega, pero en el panel se queda en *enviado* y no verás las respuestas del cliente.

Para tus propias plantillas (`promo_temporada`, `carrito_abandonado`…): las que vienen en los datos de demostración figuran como aprobadas solo en el sandbox. En modo real **duplícalas** (o créalas de nuevo), pulsa **Enviar a revisión de Meta** y espera la aprobación antes de usarlas.

## 10. Solución de problemas

| Síntoma / error de Meta | Causa | Solución |
|---|---|---|
| No llega nada y el panel muestra el aviso amarillo | Sigue en `WHATSAPP_MODE=sandbox` | Cambia a `cloud` y reinicia API **y** worker |
| `(#131030) Recipient phone number not in allowed list` | Con el número de prueba solo se puede escribir a destinatarios verificados | Paso 4: agrega tu número en **API Setup → Para → Administrar lista** |
| `(#190) Error validating access token` / sesión expirada | El token temporal dura 24 h | Genera otro en **API Setup** o crea el permanente (paso 7) |
| `(#132001) Template name does not exist in the translation` | La plantilla no existe en Meta con ese nombre **e idioma** | Revisa nombre e idioma (`hello_world` es `en_US`) o envíala a revisión |
| `(#131047) Re-engagement message` | Texto libre fuera de la ventana de 24 h | Inicia la conversación con una plantilla aprobada |
| El mensaje queda en *en cola* | El worker de Celery no está corriendo | Levanta el worker (`celery -A app.worker worker --pool=threads`) o usa `CELERY_EAGER=true` |
| El número no se reconoce | Formato incorrecto | Usa formato internacional sin `+`: `58` + `4241234567` |

Prueba directa con la API, sin pasar por el panel (útil para descartar problemas de configuración):

```bash
curl -X POST "https://graph.facebook.com/v21.0/$WHATSAPP_PHONE_NUMBER_ID/messages" \
  -H "Authorization: Bearer $WHATSAPP_TOKEN" -H "Content-Type: application/json" \
  -d '{"messaging_product":"whatsapp","to":"584241234567","type":"template",
       "template":{"name":"hello_world","language":{"code":"en_US"}}}'
```

Si este comando funciona pero el panel no, revisa que el worker esté activo y que el `.env` que lee la API sea el mismo.

## Políticas que el sistema hace cumplir

| Política de WhatsApp Business | Dónde se aplica |
|---|---|
| Solo escribir a quien dio **opt-in** | `services/envio.py` rechaza cualquier envío a contactos sin consentimiento vigente; cada alta y baja queda en la tabla `consentimientos` con fecha, origen y evidencia. |
| Respetar la **baja** inmediatamente | Mensaje entrante `BAJA`, `STOP`, `DETENER`… → opt‑out automático y confirmación. |
| Iniciar conversaciones solo con **plantillas aprobadas** | Campañas, disparadores y reenganche manual exigen estado `APROBADA`. |
| **Ventana de 24 h** para texto libre | La bandeja solo permite texto libre si el cliente escribió en las últimas 24 h; si no, ofrece enviar una plantilla. |
| **Límites de velocidad** | Limitador global en Redis (`RATE_LIMIT_MPS`) compartido por todos los workers, más reintentos con backoff exponencial ante 429/5xx y códigos de límite de Meta (130429, 131056…). |
