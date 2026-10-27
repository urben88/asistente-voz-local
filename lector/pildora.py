"""Pildora visual del lector, con el mismo diseno que la de Handy.

Abajo en el centro, siempre encima y sin robar el foco:
  - "preparando": punto gris y barras grises que laten (genera la primera frase)
  - "leyendo": punto rosa que palpita y barras rosas que siguen la voz
  - clic en la X (o el atajo otra vez) para parar

En Windows es una ventana con transparencia real (bordes redondeados suaves).
En Linux se usa una ventana normal de Tk (esquinas sin transparencia).
"""

import logging
import math
import sys
import time
import tkinter as tk
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ES_WINDOWS = sys.platform == "win32"
log = logging.getLogger("lector.pildora")

# Medidas de Handy (RecordingOverlay.css / overlay.rs), en pixeles logicos
ANCHO, ALTO = 172, 40
ANCHO_CARGA = 210  # mas ancha cuando lleva texto ("Cargando voz...")
MARGEN_ABAJO = 15
BARRAS, BARRA_ANCHO, BARRA_HUECO, BARRA_MIN, BARRA_MAX = 9, 4, 3, 3, 18
PUNTO = 7
SUPER = 4  # supermuestreo para bordes suaves

# Paletas de Handy (theme.css): superficie, borde, acento (rosa), gris
TEMAS = {
    "oscuro": {"fondo": (44, 43, 41, 250), "borde": (251, 251, 251, 31),
               "acento": (242, 140, 187), "gris": (163, 160, 154)},
    "claro": {"fondo": (251, 251, 251, 250), "borde": (128, 128, 128, 56),
              "acento": (250, 162, 202), "gris": (110, 110, 110)},
}
ROJO = (232, 106, 106)


def tema_sistema():
    if not ES_WINDOWS:
        return "oscuro"
    try:
        import winreg
        clave = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        claro, _ = winreg.QueryValueEx(clave, "AppsUseLightTheme")
        return "claro" if claro else "oscuro"
    except OSError:
        return "oscuro"


def _nivel(valor):
    """Nivel de barra utilizable: 0..1 y nunca NaN/inf (PIL revienta con NaN)."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(valor):
        return 0.0
    return min(1.0, max(0.0, valor))


@lru_cache(maxsize=8)
def _fuente(escala):
    """Fuente del sistema para el texto de la pildora (si no hay, la de PIL)."""
    tam = max(9, int(round(9 * escala * SUPER)))  # la imagen se dibuja a SUPERx
    for nombre in ("segoeui.ttf", "DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def dibujar(estado, niveles, t, escala, tema, texto=""):
    """Devuelve la pildora como imagen RGBA (pixeles fisicos)."""
    c = TEMAS[tema]
    s = escala * SUPER
    fuente = _fuente(escala)
    # Ancho: el de siempre, o el que pida el texto (estado "cargando")
    ancho = ANCHO
    ancho_texto = 0
    if texto:
        try:
            ancho_texto = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(
                texto, font=fuente) / SUPER
        except Exception:
            ancho_texto = len(texto) * 5
        ancho = max(ANCHO_CARGA, int(70 + ancho_texto + 26))
    w, h = round(ancho * s), round(ALTO * s)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=c["fondo"],
                        outline=c["borde"], width=max(1, round(s)))
    cy = h / 2

    # Punto de estado (izquierda), con el pulso de Handy cuando lee
    px = 10 * s + PUNTO * s / 2 + 2 * s
    r = PUNTO * s / 2

    if texto:
        # Con texto: aro (cargando) o punto de color + el mensaje; sin barras ni X
        if estado == "cargando":
            radio = r + 2 * s
            inicio = (t * 320) % 360
            d.arc((px - radio, cy - radio, px + radio, cy + radio), inicio, inicio + 230,
                  fill=c["gris"] + (235,), width=max(1, round(1.8 * s)))
            color_texto = c["gris"]
        else:
            color = ROJO if estado == "error" else c["gris"]
            d.ellipse((px - r, cy - r, px + r, cy + r), fill=color + (230,))
            color_texto = color
        d.text((px + r + 9 * s, cy), texto, font=fuente,
               fill=color_texto + (240,), anchor="lm")
        return img.resize((round(ancho * escala), round(ALTO * escala)), Image.LANCZOS)

    # Punto de estado (izquierda), con el pulso de Handy cuando lee
    if estado == "leyendo":
        fase = (t % 1.9) / 1.9
        if fase < 0.7:
            anillo = r + 7 * s * (fase / 0.7)
            alfa = int(70 * (1 - fase / 0.7))
            d.ellipse((px - anillo, cy - anillo, px + anillo, cy + anillo),
                      fill=c["acento"] + (alfa,))
        d.ellipse((px - r, cy - r, px + r, cy + r), fill=c["acento"] + (255,))
    else:
        d.ellipse((px - r, cy - r, px + r, cy + r), fill=c["gris"] + (115,))

    # Barras (centro)
    total = BARRAS * BARRA_ANCHO + (BARRAS - 1) * BARRA_HUECO
    x0 = (ancho - total) / 2 * s - 4 * s
    for i in range(BARRAS):
        if estado == "leyendo":
            alto = BARRA_MIN + _nivel(niveles[i]) * (BARRA_MAX - BARRA_MIN)
            color = c["acento"] + (255,)
        elif estado == "aviso":  # no habia texto: barras grises quietas
            alto, color = BARRA_MIN, c["gris"] + (110,)
        else:  # preparando: pulso gris que viaja del centro hacia fuera
            retraso = abs(i - BARRAS // 2) * 0.075
            fase = 0.5 - 0.5 * math.cos(2 * math.pi * ((t - retraso) % 0.9) / 0.9)
            alto = 6 * (0.55 + 0.95 * fase)
            color = c["gris"] + (int(255 * (0.25 + 0.45 * fase)),)
        bx = x0 + i * (BARRA_ANCHO + BARRA_HUECO) * s
        bh = alto * s
        d.rounded_rectangle((bx, cy - bh / 2, bx + BARRA_ANCHO * s, cy + bh / 2),
                            radius=2 * s, fill=color)

    # X para parar (derecha)
    xc, xr = w - (10 + 11) * s, 3.5 * s
    for a, b in (((xc - xr, cy - xr), (xc + xr, cy + xr)), ((xc - xr, cy + xr), (xc + xr, cy - xr))):
        d.line((a, b), fill=c["gris"] + (200,), width=round(1.6 * s))

    return img.resize((round(ANCHO * escala), round(ALTO * escala)), Image.LANCZOS)


class _CapaWindows:
    """Ventana con alfa por pixel (UpdateLayeredWindow)."""

    def __init__(self, raiz):
        import ctypes
        from ctypes import wintypes as wt

        self.ct = ctypes
        u, g = ctypes.windll.user32, ctypes.windll.gdi32
        self.u, self.g = u, g
        vp = ctypes.c_void_p
        u.GetDC.restype = vp
        u.GetDC.argtypes = [vp]
        u.ReleaseDC.argtypes = [vp, vp]
        g.CreateCompatibleDC.restype = vp
        g.CreateCompatibleDC.argtypes = [vp]
        g.CreateDIBSection.restype = vp
        g.CreateDIBSection.argtypes = [vp, vp, ctypes.c_uint, ctypes.POINTER(vp), vp, ctypes.c_uint]
        g.SelectObject.restype = vp
        g.SelectObject.argtypes = [vp, vp]
        g.DeleteObject.argtypes = [vp]
        g.DeleteDC.argtypes = [vp]
        u.ShowWindow.argtypes = [vp, ctypes.c_int]
        u.GetWindowLongW.argtypes = [vp, ctypes.c_int]
        u.SetWindowLongW.argtypes = [vp, ctypes.c_int, ctypes.c_long]

        class BLEND(ctypes.Structure):
            _fields_ = [("op", ctypes.c_ubyte), ("flags", ctypes.c_ubyte),
                        ("alfa", ctypes.c_ubyte), ("formato", ctypes.c_ubyte)]

        class BMIH(ctypes.Structure):
            _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                        ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                        ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", wt.LONG),
                        ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                        ("biClrImportant", wt.DWORD)]

        self.BLEND, self.BMIH, self.wt = BLEND, BMIH, wt
        u.UpdateLayeredWindow.argtypes = [vp, vp, ctypes.POINTER(wt.POINT), ctypes.POINTER(wt.SIZE), vp,
                                          ctypes.POINTER(wt.POINT), ctypes.c_uint,
                                          ctypes.POINTER(BLEND), ctypes.c_uint]

        raiz.update_idletasks()
        self.hwnd = int(raiz.wm_frame(), 16)
        # WS_EX_LAYERED | WS_EX_TOOLWINDOW (sin barra de tareas) | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        estilo = u.GetWindowLongW(self.hwnd, -20)
        u.SetWindowLongW(self.hwnd, -20, estilo | 0x80000 | 0x80 | 0x08000000 | 0x8)
        self.visible = False

    def mostrar(self, img, x, y, alfa):
        ct, u, g, wt = self.ct, self.u, self.g, self.wt
        a = np.asarray(img, dtype=np.uint16)
        bgra = np.empty(a.shape, dtype=np.uint8)  # alfa premultiplicado, orden BGRA
        bgra[..., 0] = a[..., 2] * a[..., 3] // 255
        bgra[..., 1] = a[..., 1] * a[..., 3] // 255
        bgra[..., 2] = a[..., 0] * a[..., 3] // 255
        bgra[..., 3] = a[..., 3]
        h, w = bgra.shape[:2]

        cabecera = self.BMIH(ct.sizeof(self.BMIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        pantalla = u.GetDC(None)
        dc = g.CreateCompatibleDC(pantalla)
        bits = ct.c_void_p()
        mapa = g.CreateDIBSection(dc, ct.byref(cabecera), 0, ct.byref(bits), None, 0)
        ct.memmove(bits, bgra.tobytes(), bgra.nbytes)
        anterior = g.SelectObject(dc, mapa)
        u.UpdateLayeredWindow(self.hwnd, pantalla, ct.byref(wt.POINT(x, y)), ct.byref(wt.SIZE(w, h)),
                              dc, ct.byref(wt.POINT(0, 0)), 0,
                              ct.byref(self.BLEND(0, 0, alfa, 1)), 2)  # AC_SRC_ALPHA, ULW_ALPHA
        g.SelectObject(dc, anterior)
        g.DeleteObject(mapa)
        g.DeleteDC(dc)
        u.ReleaseDC(None, pantalla)
        if not self.visible:
            u.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
            self.visible = True

    def ocultar(self):
        if self.visible:
            self.u.ShowWindow(self.hwnd, 0)
            self.visible = False


class _CapaTk:
    """Linux: ventana Tk sin bordes (sin transparencia por pixel)."""

    def __init__(self, raiz):
        from PIL import ImageTk
        self.ImageTk, self.raiz = ImageTk, raiz
        self.etiqueta = tk.Label(raiz, bd=0, highlightthickness=0)
        self.etiqueta.pack()
        self.visible = False

    def mostrar(self, img, x, y, alfa):
        fondo = Image.new("RGBA", img.size, TEMAS["oscuro"]["fondo"][:3] + (255,))
        self.foto = self.ImageTk.PhotoImage(Image.alpha_composite(fondo, img))
        self.etiqueta.configure(image=self.foto)
        self.raiz.geometry(f"{img.size[0]}x{img.size[1]}+{x}+{y}")
        self.raiz.attributes("-alpha", alfa / 255)
        if not self.visible:
            self.raiz.deiconify()
            self.visible = True

    def ocultar(self):
        if self.visible:
            self.raiz.withdraw()
            self.visible = False


class Pildora:
    """Refresca la pildora ~30 veces por segundo segun lector.estado y lector.niveles."""

    def __init__(self, lector):
        self.lector = lector
        if ES_WINDOWS:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except OSError:
                pass
        self.raiz = tk.Tk()
        self.raiz.overrideredirect(True)
        self.raiz.attributes("-topmost", True)
        self.raiz.geometry("1x1+-100+-100")
        self.capa = _CapaWindows(self.raiz) if ES_WINDOWS else _CapaTk(self.raiz)
        if not ES_WINDOWS:
            self.raiz.withdraw()
        self.raiz.bind("<Button-1>", self._clic)
        self.tema = tema_sistema()
        self.niveles = [0.0] * BARRAS
        self.alfa = 0.0
        self.ultimo = "preparando"
        self.t0 = time.monotonic()
        self.cerrando = False
        self.ultimo_error = 0.0

    def _escala(self):
        if ES_WINDOWS:
            import ctypes
            return ctypes.windll.user32.GetDpiForSystem() / 96
        return 1.0

    def _posicion(self, w, h, escala):
        if ES_WINDOWS:
            import ctypes
            from ctypes import wintypes
            area = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(area), 0)  # SPI_GETWORKAREA
            izq, der, abajo = area.left, area.right, area.bottom
        else:
            izq, der, abajo = 0, self.raiz.winfo_screenwidth(), self.raiz.winfo_screenheight() - 48
        return izq + (der - izq - w) // 2, abajo - h - round(MARGEN_ABAJO * escala)

    def _clic(self, _evento):
        if self.lector.estado in ("preparando", "leyendo"):
            self.lector.alternar()  # leyendo -> para

    def _tick(self):
        """Refresco periodico. Si un fotograma falla, el bucle sigue: nunca se congela
        en pantalla (un error suelto dejaba la pildora clavada, sin desaparecer)."""
        if self.cerrando:
            self.raiz.destroy()
            return
        try:
            self._pintar()
        except Exception:
            ahora = time.monotonic()
            if ahora - self.ultimo_error > 5:  # no llenar el log 30 veces por segundo
                self.ultimo_error = ahora
                log.exception("Error dibujando la pildora: se oculta hasta el proximo aviso")
            self.alfa = 0.0
            try:
                self.capa.ocultar()
            except Exception:
                pass
        self.raiz.after(33, self._tick)

    def _pintar(self):
        estado = self.lector.estado
        ahora = time.monotonic()
        if estado == "inactivo":
            if getattr(self.lector, "error_hasta", 0.0) > ahora:
                estado = "error"
            elif getattr(self.lector, "aviso_hasta", 0.0) > ahora:
                estado = "aviso"
        visible = estado != "inactivo"
        if estado == "cargando" and not getattr(self.lector, "cargando_visible", False):
            visible = False  # carga inicial en segundo plano: no molestar
        objetivo = 1.0 if visible else 0.0
        # Aparece y desaparece en ~200 ms, como Handy
        self.alfa += max(-0.17, min(0.17, objetivo - self.alfa))
        if self.alfa <= 0.01:
            self.capa.ocultar()
            self.niveles = [0.0] * BARRAS
        else:
            if not self.capa.visible:
                self.tema = tema_sistema()  # por si cambio claro/oscuro
            self._suavizar(estado)
            escala = self._escala()
            if visible:
                self.ultimo = estado  # al desvanecerse se mantiene el ultimo dibujo
            texto = ""
            if self.ultimo == "cargando" and estado in ("cargando", "inactivo"):
                desde = getattr(self.lector, "cargando_desde", None)
                segundos = int(time.monotonic() - desde) if desde else 0
                texto = f"Cargando voz… {segundos} s" if segundos >= 1 else "Cargando voz…"
            elif self.ultimo == "error" and estado in ("error", "inactivo"):
                texto = getattr(self.lector, "error_texto", "") or "No se pudo cargar la voz"
            elif self.ultimo == "aviso" and estado in ("aviso", "inactivo"):
                texto = getattr(self.lector, "aviso_texto", "") or "Nada que leer"
            img = dibujar(self.ultimo, self.niveles,
                          time.monotonic() - self.t0, escala, self.tema, texto)
            x, y = self._posicion(img.size[0], img.size[1], escala)
            self.capa.mostrar(img, x, y, int(255 * self.alfa))

    def _suavizar(self, estado):
        """Niveles de las barras con memoria (0,7 + 0,3) y saneados: siempre 9 valores 0..1."""
        nuevos = list(self.lector.niveles)[:BARRAS] if estado != "inactivo" else []
        nuevos += [0.0] * (BARRAS - len(nuevos))
        self.niveles = [p * 0.7 + _nivel(n) * 0.3 for p, n in zip(self.niveles, nuevos)]

    def ejecutar(self):
        self.raiz.after(33, self._tick)
        self.raiz.mainloop()

    def cerrar(self):
        """Se puede llamar desde otro hilo (el del atajo): Tk se toca solo desde su bucle."""
        self.cerrando = True
