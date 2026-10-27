"""Aviso flotante del panel (abajo al centro), sin robar el foco.

Se usa cuando el lector está apagado y se pulsa Ctrl+Alt+R: no hay proceso que
pueda mostrar la píldora, así que avisa el panel.
"""

import logging

import tkinter as tk

log = logging.getLogger("panel.toast")

FONDO = "#2c2b29"
TEXTO = "#fbfbfb"
ACENTO = "#f28cbb"
FAMILIA = "Segoe UI" if __import__("sys").platform == "win32" else "DejaVu Sans"

_ABIERTOS = []


def mostrar(raiz, texto, segundos=3.5):
    """Muestra un aviso flotante y lo cierra solo. Nunca lanza."""
    try:
        ventana = tk.Toplevel(raiz)
        ventana.overrideredirect(True)
        ventana.attributes("-topmost", True)
        ventana.configure(bg=FONDO)
        etiqueta = tk.Label(ventana, text=texto, bg=FONDO, fg=TEXTO,
                            font=(FAMILIA, 10), padx=16, pady=10, justify="left",
                            wraplength=int(360 * _escala(raiz)))
        etiqueta.pack()
        ventana.update_idletasks()
        ancho, alto = ventana.winfo_reqwidth(), ventana.winfo_reqheight()
        pantalla = raiz.winfo_screenwidth() if raiz is not None else 1920
        alto_pantalla = raiz.winfo_screenheight() if raiz is not None else 1080
        x = (pantalla - ancho) // 2
        y = alto_pantalla - alto - int(70 * _escala(raiz))
        ventana.geometry(f"+{max(0, x)}+{max(0, y)}")
        _ABIERTOS.append(ventana)

        def cerrar():
            try:
                if ventana in _ABIERTOS:
                    _ABIERTOS.remove(ventana)
                ventana.destroy()
            except tk.TclError:
                pass

        ventana.after(max(1, int(segundos * 1000)), cerrar)
        return ventana
    except Exception:
        log.exception("No se pudo mostrar el aviso")
        return None


def _escala(widget):
    try:
        return max(1.0, widget.winfo_fpixels("1i") / 96.0)
    except (tk.TclError, AttributeError):
        return 1.0


def cerrar_todos():
    for ventana in list(_ABIERTOS):
        try:
            ventana.destroy()
        except tk.TclError:
            pass
    _ABIERTOS.clear()
