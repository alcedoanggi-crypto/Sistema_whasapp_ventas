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

## Políticas que el sistema hace cumplir

| Política de WhatsApp Business | Dónde se aplica |
|---|---|
| Solo escribir a quien dio **opt-in** | `services/envio.py` rechaza cualquier envío a contactos sin consentimiento vigente; cada alta y baja queda en la tabla `consentimientos` con fecha, origen y evidencia. |
| Respetar la **baja** inmediatamente | Mensaje entrante `BAJA`, `STOP`, `DETENER`… → opt‑out automático y confirmación. |
| Iniciar conversaciones solo con **plantillas aprobadas** | Campañas, disparadores y reenganche manual exigen estado `APROBADA`. |
| **Ventana de 24 h** para texto libre | La bandeja solo permite texto libre si el cliente escribió en las últimas 24 h; si no, ofrece enviar una plantilla. |
| **Límites de velocidad** | Limitador global en Redis (`RATE_LIMIT_MPS`) compartido por todos los workers, más reintentos con backoff exponencial ante 429/5xx y códigos de límite de Meta (130429, 131056…). |
