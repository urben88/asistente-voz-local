"""Icono de la bandeja del panel de voz (spec 07, R8).

El icono se dibuja con Pillow (mismo rosa que la pildora) y ``pystray`` lo pone
en la bandeja. ``crear_icono()`` solo construye el objeto; el panel lo ejecuta en
un hilo daemon con ``icono.run()``.
"""

import logging

log = logging.getLogger("panel.icono")

FONDO = (44, 43, 41)
ACENTO = (242, 140, 187)
TEXTO = (251, 251, 251)


def generar_imagen(tam=64):
    """Icono RGBA: fondo oscuro redondeado con un circulo rosa."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margen = 2
    d.rounded_rectangle((margen, margen, tam - margen - 1, tam - margen - 1),
                        radius=tam // 4, fill=FONDO + (255,))
    r = tam * 0.28
    cx = cy = tam / 2
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACENTO + (255,))
    return img


def crear_icono(on_abrir, on_lector, on_salir, esta):
    """Icono de bandeja con el menu del panel.

    ``esta()`` devuelve el estado actual (``{"lector": ...}``) y se consulta cada
    vez que pystray redibuja el menu, asi que basta con ``icono.update_menu()``
    cuando cambie.
    """
    import pystray

    def estado_actual():
        try:
            return esta() or {}
        except Exception:
            log.exception("No se pudo leer el estado para el icono")
            return {}

    menu = pystray.Menu(
        pystray.MenuItem("Abrir panel", lambda _i, _it: on_abrir(), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda _it: "Lector: encendido" if estado_actual().get("lector") else "Lector: apagado",
            lambda _i, _it: on_lector(not estado_actual().get("lector")),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", lambda _i, _it: on_salir()),
    )
    return pystray.Icon("asistente-voz-local", generar_imagen(), "Panel de voz", menu)
