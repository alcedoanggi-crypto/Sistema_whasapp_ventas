"""Variables dinámicas de plantillas: {{nombre}}, {{producto}}, {{descuento}}...

Usamos parámetros *con nombre* (parameter_format=NAMED de la Cloud API) en lugar de los
posicionales {{1}}, {{2}}: el mismo texto sirve para la vista previa, el render local y Meta.
"""
import re

PATRON_VARIABLE = re.compile(r"\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}")
PATRON_NOMBRE_PLANTILLA = re.compile(r"^[a-z0-9_]{1,512}$")

# Variables que se resuelven a partir del contacto; el resto debe venir de la campaña o del evento.
VARIABLES_DE_CONTACTO = {"nombre", "nombre_completo", "telefono"}


def extraer_variables(*textos: str | None) -> list[str]:
    vistas: list[str] = []
    for texto in textos:
        for nombre in PATRON_VARIABLE.findall(texto or ""):
            if nombre not in vistas:
                vistas.append(nombre)
    return vistas


def renderizar(texto: str | None, valores: dict) -> str:
    if not texto:
        return ""
    return PATRON_VARIABLE.sub(lambda m: str(valores.get(m.group(1), m.group(0))), texto)


def variables_de_contacto(contacto) -> dict:
    nombre = (contacto.nombre or "").strip()
    return {
        "nombre": nombre.split()[0] if nombre else "cliente",
        "nombre_completo": nombre or "cliente",
        "telefono": contacto.telefono,
    }


def faltantes(plantilla, valores: dict) -> list[str]:
    return [
        v
        for v in extraer_variables(plantilla.encabezado, plantilla.cuerpo)
        if str(valores.get(v, "")).strip() == ""
    ]


def texto_completo(plantilla, valores: dict) -> str:
    partes = [
        f"*{renderizar(plantilla.encabezado, valores)}*" if plantilla.encabezado else None,
        renderizar(plantilla.cuerpo, valores),
        f"_{plantilla.pie}_" if plantilla.pie else None,
    ]
    return "\n\n".join(p for p in partes if p)


def componentes_envio(plantilla, valores: dict) -> list[dict]:
    """Bloque `template.components` del POST /messages."""
    componentes = []
    for tipo, texto in (("header", plantilla.encabezado), ("body", plantilla.cuerpo)):
        nombres = extraer_variables(texto)
        if nombres:
            componentes.append(
                {
                    "type": tipo,
                    "parameters": [
                        {"type": "text", "parameter_name": n, "text": str(valores[n])} for n in nombres
                    ],
                }
            )
    return componentes


def componentes_registro(plantilla) -> list[dict]:
    """Bloque `components` del POST /{WABA_ID}/message_templates (alta de la plantilla en Meta)."""
    ejemplos = plantilla.ejemplos or {}

    def ejemplos_de(texto):
        return [{"param_name": n, "example": ejemplos.get(n, n)} for n in extraer_variables(texto)]

    componentes = []
    if plantilla.encabezado:
        header = {"type": "HEADER", "format": "TEXT", "text": plantilla.encabezado}
        if ej := ejemplos_de(plantilla.encabezado):
            header["example"] = {"header_text_named_params": ej}
        componentes.append(header)
    body = {"type": "BODY", "text": plantilla.cuerpo}
    if ej := ejemplos_de(plantilla.cuerpo):
        body["example"] = {"body_text_named_params": ej}
    componentes.append(body)
    if plantilla.pie:
        componentes.append({"type": "FOOTER", "text": plantilla.pie})
    if plantilla.botones:
        componentes.append(
            {"type": "BUTTONS", "buttons": [{"type": "QUICK_REPLY", "text": b} for b in plantilla.botones]}
        )
    return componentes
