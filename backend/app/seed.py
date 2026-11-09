"""Datos de demostración:  python -m app.seed --reset

Crea plantillas, disparadores, respuestas automáticas, contactos con su consentimiento
y dos campañas pasadas con historial realista para que el dashboard tenga datos desde el inicio.
"""
import random
import sys
import uuid
from datetime import timedelta

from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.models import (
    Campana,
    Contacto,
    Disparador,
    EventoNegocio,
    Mensaje,
    Plantilla,
    RespuestaAutomatica,
    ahora,
)
from app.services import consentimientos
from app.services import plantillas as tpl

random.seed(7)

PLANTILLAS = [
    dict(
        nombre="promo_temporada",
        categoria="MARKETING",
        encabezado="🔥 Oferta para ti, {{nombre}}",
        cuerpo="Hola {{nombre}}, esta semana tu {{producto}} favorito tiene {{descuento}} de descuento. "
        "Válido hasta agotar existencias.",
        pie="Responde BAJA para no recibir promociones",
        botones=["Ver catálogo", "Hablar con un asesor"],
        ejemplos={"nombre": "Ana", "producto": "Zapatillas Run X", "descuento": "20%"},
    ),
    dict(
        nombre="bienvenida_cliente",
        categoria="MARKETING",
        cuerpo="¡Hola {{nombre}}! 👋 Gracias por suscribirte. Aquí recibirás ofertas exclusivas y novedades. "
        "Escribe CATALOGO para ver nuestros productos.",
        pie="Responde BAJA para darte de baja",
        ejemplos={"nombre": "Ana"},
    ),
    dict(
        nombre="carrito_abandonado",
        categoria="MARKETING",
        cuerpo="{{nombre}}, dejaste {{producto}} en tu carrito 🛒. Lo guardamos por ti: completa tu compra hoy "
        "y recibe envío gratis.",
        pie="Responde BAJA para no recibir recordatorios",
        botones=["Completar compra"],
        ejemplos={"nombre": "Ana", "producto": "Zapatillas Run X"},
    ),
    dict(
        nombre="recordatorio_pago",
        categoria="UTILITY",
        cuerpo="Hola {{nombre}}, te recordamos que el pago de tu pedido {{pedido}} por {{monto}} vence el "
        "{{vencimiento}}. Si ya pagaste, ignora este mensaje.",
        ejemplos={"nombre": "Ana", "pedido": "#1042", "monto": "$59,90", "vencimiento": "15/11"},
    ),
    dict(
        nombre="seguimiento_postventa",
        categoria="MARKETING",
        cuerpo="¡Hola {{nombre}}! ¿Qué tal te pareció tu {{producto}}? Tu opinión nos ayuda mucho. "
        "Responde del 1 al 5 ⭐",
        pie="Responde BAJA para no recibir mensajes",
        ejemplos={"nombre": "Ana", "producto": "Zapatillas Run X"},
    ),
    dict(
        nombre="lanzamiento_coleccion",
        categoria="MARKETING",
        cuerpo="{{nombre}}, llegó la nueva colección de {{producto}}. Los primeros 50 pedidos tienen {{descuento}} OFF.",
        pie="Responde BAJA para no recibir promociones",
        ejemplos={"nombre": "Ana", "producto": "invierno", "descuento": "15%"},
    ),
]

DISPARADORES = [
    ("bienvenida", "Al registrar un contacto con opt-in", "bienvenida_cliente", 1),
    ("carrito_abandonado", "Si no compra tras abandonar el carrito", "carrito_abandonado", 60),
    ("recordatorio_pago", "Cuando hay un pago pendiente", "recordatorio_pago", 1),
    ("post_venta", "Días después de una compra", "seguimiento_postventa", 60 * 24 * 3),
]

RESPUESTAS = [
    ("Precios", ["precio", "precios", "cuanto cuesta", "costo", "valor"], 10,
     "Hola {{nombre}} 💰 Nuestros precios están en el catálogo: https://tienda.demo/catalogo. "
     "¿Te ayudo con algún producto en particular?"),
    ("Horarios", ["horario", "horarios", "abren", "cierran", "atencion"], 5,
     "🕘 Atendemos de lunes a viernes de 9:00 a 18:00 y sábados de 9:00 a 13:00."),
    ("Catálogo", ["catalogo", "productos", "ver catalogo"], 5,
     "📒 Mira el catálogo completo aquí: https://tienda.demo/catalogo"),
    ("Envíos", ["envio", "envios", "domicilio", "delivery"], 1,
     "🚚 Hacemos envíos a todo el país. Gratis en compras superiores a $50."),
]

NOMBRES = (
    "Ana Pérez,Luis Gómez,María Rodríguez,Carlos Díaz,Lucía Fernández,Jorge Martínez,Valentina Torres,"
    "Andrés Ramírez,Camila Flores,Diego Morales,Sofía Herrera,Pedro Castillo,Daniela Rojas,Miguel Vargas,"
    "Gabriela Mendoza,José Silva,Paula Castro,Ricardo Ortiz,Isabel Núñez,Fernando Rivas,Carolina León,"
    "Alejandro Medina,Natalia Guerrero,Sebastián Ríos,Mariana Aguilar,Tomás Navarro,Elena Campos,"
    "Manuel Cabrera,Adriana Soto,Héctor Paredes,Laura Molina,Raúl Delgado,Patricia Vega,Iván Fuentes,"
    "Teresa Salazar,Óscar Pineda"
).split(",")
ETIQUETAS = ["vip", "nuevo", "calzado", "ropa", "accesorios", "caracas", "valencia"]
ORIGENES = ["formulario_web", "checkout", "tienda_fisica", "checkout", "formulario_web"]


def reset() -> None:
    with engine.begin() as conn:
        tablas = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))


def sembrar() -> None:
    db = SessionLocal()
    now = ahora()

    plantillas = {}
    for datos in PLANTILLAS:
        p = Plantilla(**datos, estado="APROBADA", meta_id=f"sandbox-{uuid.uuid4().hex[:10]}")
        db.add(p)
        plantillas[p.nombre] = p
    db.add(
        Plantilla(
            nombre="borrador_black_friday",
            cuerpo="{{nombre}}, el Black Friday llega con {{descuento}} en {{producto}}. ¡Prepárate!",
            pie="Responde BAJA para no recibir promociones",
            ejemplos={"nombre": "Ana", "producto": "toda la tienda", "descuento": "40%"},
        )
    )
    db.flush()

    for tipo, desc, nombre_p, retraso in DISPARADORES:
        db.add(Disparador(tipo=tipo, descripcion=desc, activo=True, plantilla_id=plantillas[nombre_p].id, retraso_minutos=retraso))
    for nombre, claves, prioridad, respuesta in RESPUESTAS:
        db.add(RespuestaAutomatica(nombre=nombre, palabras_clave=claves, respuesta=respuesta, prioridad=prioridad))

    contactos = []
    for i, nombre in enumerate(NOMBRES):
        c = Contacto(
            telefono=f"58412{1000000 + i * 7919:07d}",
            nombre=nombre,
            email=f"{nombre.split()[0].lower()}@correo.demo".replace("ó", "o").replace("í", "i").replace("é", "e")
            .replace("á", "a").replace("ú", "u"),
            etiquetas=sorted(random.sample(ETIQUETAS, random.randint(1, 3))),
            creado=now - timedelta(days=random.randint(20, 90)),
        )
        db.add(c)
        consentimientos.registrar_opt_in(
            db, c, random.choice(ORIGENES), "Casilla 'Acepto recibir ofertas por WhatsApp' marcada", c.creado
        )
        contactos.append(c)
    # Dos bajas reales para que se vea el historial de consentimiento
    for c in contactos[-2:]:
        consentimientos.registrar_opt_out(db, c, "palabra_clave", 'Respondió "BAJA"', now - timedelta(days=3))
    db.flush()

    _campana_historica(db, "Promo zapatillas octubre", plantillas["promo_temporada"],
                       {"producto": "Zapatillas Run X", "descuento": "25%"}, {"etiquetas": ["calzado", "vip"]},
                       now - timedelta(days=12), contactos)
    _campana_historica(db, "Nueva colección invierno", plantillas["lanzamiento_coleccion"],
                       {"producto": "invierno", "descuento": "15%"}, {"etiquetas": []},
                       now - timedelta(days=4), contactos)
    db.add(
        Campana(
            nombre="Recordatorio fin de mes (programada)",
            plantilla_id=plantillas["promo_temporada"].id,
            segmento={"etiquetas": ["vip"], "modo": "cualquiera"},
            variables={"producto": "accesorio", "descuento": "10%"},
            estado="PROGRAMADA",
            programada_para=now + timedelta(days=2),
        )
    )
    db.commit()
    db.close()
    print(f"Listo: {len(contactos)} contactos, {len(PLANTILLAS) + 1} plantillas, 3 campañas.")


def _campana_historica(db, nombre, plantilla, variables, segmento, inicio, contactos):
    c = Campana(nombre=nombre, plantilla_id=plantilla.id, segmento=segmento, variables=variables,
                estado="COMPLETADA", programada_para=inicio, iniciada=inicio, finalizada=inicio + timedelta(minutes=3))
    db.add(c)
    db.flush()
    etiquetas = set(segmento["etiquetas"])
    destinatarios = [x for x in contactos if not etiquetas or etiquetas & set(x.etiquetas)]
    for contacto in destinatarios:
        valores = {**tpl.variables_de_contacto(contacto), **variables}
        t = inicio + timedelta(seconds=random.randint(1, 180))
        m = Mensaje(contacto=contacto, campana_id=c.id, plantilla_id=plantilla.id, origen="campana",
                    direccion="saliente", tipo="plantilla", contenido=tpl.texto_completo(plantilla, valores),
                    variables=variables, wamid=f"wamid.SANDBOX.{uuid.uuid4().hex}", creado=t, enviado_en=t, intentos=1)
        r = random.random()
        if r < 0.05:
            m.estado, m.fallido_en, m.error_codigo = "fallido", t, 131026
            m.error = "[131026] Message undeliverable. El número no tiene WhatsApp"
        else:
            m.estado, m.entregado_en = "entregado", t + timedelta(seconds=random.randint(2, 60))
            if r < 0.72:
                m.estado, m.leido_en = "leido", m.entregado_en + timedelta(minutes=random.randint(1, 600))
                if random.random() < 0.35:
                    m.respondido_en = m.leido_en + timedelta(minutes=random.randint(1, 30))
                    db.add(Mensaje(contacto=contacto, origen="cliente", direccion="entrante", tipo="text",
                                   contenido=random.choice(["¿Cuál es el precio?", "Me interesa 😍", "¿Tienen talla 40?",
                                                            "Gracias!", "¿Hacen envíos?"]),
                                   wamid=f"wamid.SANDBOX.IN.{uuid.uuid4().hex}", estado="recibido", creado=m.respondido_en))
                    contacto.ultimo_entrante = m.respondido_en
                    contacto.no_leidos = random.choice([0, 0, 1])
                    if random.random() < 0.5:
                        monto = round(random.uniform(25, 140), 2)
                        db.add(EventoNegocio(contacto=contacto, tipo="compra", referencia=f"ped-{uuid.uuid4().hex[:6]}",
                                             datos={"producto": variables["producto"]}, monto=monto, campana_id=c.id,
                                             disparo_estado="omitido", creado=m.respondido_en + timedelta(hours=2)))
        db.add(m)
        contacto.ultimo_mensaje = max(filter(None, [contacto.ultimo_mensaje, contacto.ultimo_entrante, t]))
    c.total_destinatarios = len(destinatarios)


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset()
    sembrar()
