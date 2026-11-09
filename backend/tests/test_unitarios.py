"""Pruebas unitarias sin base de datos ni Redis:  pytest -q"""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Plantilla
from app.schemas import normalizar_telefono
from app.services import plantillas as tpl
from app.services.webhook import PALABRAS_BAJA, normalizar
from app.whatsapp.firma import firma_valida, firmar


# ---------------------------------------------------------------- firma del webhook
def test_firma_valida_y_alterada():
    cuerpo = b'{"object":"whatsapp_business_account","entry":[]}'
    cabecera = firmar(cuerpo, "secreto")
    assert firma_valida(cuerpo, cabecera, "secreto")
    assert not firma_valida(cuerpo + b" ", cabecera, "secreto")  # 1 byte distinto invalida
    assert not firma_valida(cuerpo, cabecera, "otro-secreto")
    assert not firma_valida(cuerpo, None, "secreto")
    assert not firma_valida(cuerpo, "md5=abc", "secreto")
    assert not firma_valida(cuerpo, cabecera, "")  # sin App Secret no se acepta nada


cliente = TestClient(app)


def test_webhook_rechaza_firma_invalida_antes_de_tocar_la_bd():
    r = cliente.post("/webhook", content=b"{}", headers={"X-Hub-Signature-256": "sha256=00"})
    assert r.status_code == 401


def test_webhook_handshake():
    ok = cliente.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": settings.whatsapp_verify_token, "hub.challenge": "777"})
    assert ok.status_code == 200 and ok.text == "777"
    mal = cliente.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"})
    assert mal.status_code == 403


def test_api_protegida_sin_token():
    assert cliente.get("/api/contactos").status_code == 401


# ---------------------------------------------------------------- plantillas
PROMO = Plantilla(
    nombre="promo",
    idioma="es",
    categoria="MARKETING",
    encabezado="Oferta para {{nombre}}",
    cuerpo="Hola {{nombre}}, tu {{producto}} tiene {{ descuento }} de descuento",
    pie="Responde BAJA",
    botones=["Ver catálogo"],
    ejemplos={"nombre": "Ana", "producto": "Run X", "descuento": "20%"},
)


def test_extraer_variables_en_orden_y_sin_repetir():
    assert tpl.extraer_variables(PROMO.encabezado, PROMO.cuerpo) == ["nombre", "producto", "descuento"]


def test_renderizar_deja_visibles_las_que_faltan():
    assert tpl.renderizar("Hola {{nombre}} {{x}}", {"nombre": "Ana"}) == "Hola Ana {{x}}"


def test_faltantes():
    assert tpl.faltantes(PROMO, {"nombre": "Ana", "producto": " "}) == ["producto", "descuento"]


def test_componentes_envio_usa_parametros_con_nombre():
    comp = tpl.componentes_envio(PROMO, {"nombre": "Ana", "producto": "Run X", "descuento": "20%"})
    assert comp[0]["type"] == "header"
    body = comp[1]
    assert body["type"] == "body"
    assert [p["parameter_name"] for p in body["parameters"]] == ["nombre", "producto", "descuento"]
    assert body["parameters"][2]["text"] == "20%"


def test_componentes_registro_incluye_ejemplos_y_botones():
    comp = {c["type"]: c for c in tpl.componentes_registro(PROMO)}
    assert comp["BODY"]["example"]["body_text_named_params"][1] == {"param_name": "producto", "example": "Run X"}
    assert comp["HEADER"]["example"]["header_text_named_params"][0]["example"] == "Ana"
    assert comp["BUTTONS"]["buttons"] == [{"type": "QUICK_REPLY", "text": "Ver catálogo"}]
    json.dumps(comp)  # serializable tal cual para la Graph API


def test_variables_de_contacto_usa_primer_nombre():
    class C:
        nombre, telefono = "  María José Pérez ", "584120000000"

    assert tpl.variables_de_contacto(C)["nombre"] == "María"


# ---------------------------------------------------------------- baja automática y teléfonos
@pytest.mark.parametrize("texto", ["BAJA", "baja", " Stop! ", "stop.", "Detener", "no más mensajes"])
def test_palabras_de_baja(texto):
    assert normalizar(texto) in PALABRAS_BAJA


@pytest.mark.parametrize("texto", ["bajar precio", "no pares", "stop it please"])
def test_frases_que_no_son_baja(texto):
    assert normalizar(texto) not in PALABRAS_BAJA


def test_normalizar_telefono():
    assert normalizar_telefono("+58 (412) 123-4567") == "584121234567"
    with pytest.raises(ValueError):
        normalizar_telefono("123")
