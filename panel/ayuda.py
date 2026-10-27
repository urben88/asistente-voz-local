"""Ayudas escondidas del panel: tooltips, ventanas de ayuda y guia de voces.

Todo es solo lectura: ni escribe estado ni toca el lector. Los textos viven aqui
para que ``panel.py`` quede solo con la maquetacion. Nunca lanzan: si Tk falla,
se registra y se sigue (el panel debe abrir igual).
"""

import logging
import sys
import tkinter as tk
from tkinter import ttk

try:
    from . import estado, voces
except ImportError:  # lanzado como script suelto desde panel/
    import estado
    import voces

log = logging.getLogger("panel.ayuda")

FONDO = "#2c2b29"
TARJETA = "#3a3936"
TEXTO = "#fbfbfb"
GRIS = "#a3a09a"
ACENTO = "#f28cbb"
BORDE = "#5a5853"
FAMILIA = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"

# clave -> (titulo, texto). Contenido cerrado: no cambiar los datos.
AYUDAS = {
    "lector": ("Lector de voz",
               "Enciende o apaga el lector.\n\n"
               "• Encendido: queda en segundo plano con la voz cargada y responde a "
               "Ctrl+Alt+R. Con Piper ocupa ~50-80 MB de RAM; con Kokoro, ~450 MB. "
               "Nunca usa GPU.\n"
               "• Apagado: el proceso se cierra y no consume nada. Al encenderlo tarda "
               "entre 2 y 6 s en cargar la voz.\n"
               "• El dictado (Ctrl+Alt+Espacio) funciona igual esté encendido o apagado: "
               "son independientes."),
    "idioma": ("Idioma",
               "Elige con qué voz se lee. No traduce: solo cambia la pronunciación.\n\n"
               "• Español: voces de España, México o Argentina.\n"
               "• English: voces de EE. UU. o Reino Unido.\n"
               "• Cada idioma recuerda su motor y su voz. Si no hay ninguna voz de ese "
               "idioma, el panel no cambia nada y te ofrece descargarla."),
    "motor": ("Motor de voz",
              "Hay cuatro motores:\n\n"
              "• Piper (recomendado para el día a día): CPU, voces de 60-110 MB, entre 20 y 37 "
              "veces más rápido que el tiempo real. Muchos acentos.\n"
              "• Kokoro: CPU, ~450 MB de RAM. El inglés es su punto fuerte; en español solo hay "
              "3 voces y suena más plano. 3,6 veces más rápido que el tiempo real.\n"
              "• Chatterbox (GPU, ~3,2 GB de VRAM): la voz más natural en español. Genera 1,3 "
              "veces más lento de lo que habla, así que puede hacer pausas entre frases, y tarda "
              "~20 s en cargar la primera vez.\n"
              "• XTTS (GPU, ~1,8 GB de VRAM): 58 voces y 17 idiomas, 1,6 veces más rápido que el "
              "tiempo real. Acento neutro tirando a latinoamericano.\n\n"
              "En CPU: Piper/Kokoro. En GPU: Chatterbox/XTTS (comparten tarjeta con Handy y "
              "Ollama)."),
    "velocidad": ("Velocidad",
                  "Ritmo de lectura: Lenta (0,9×), Normal (1,0×) y Rápida (1,1×). "
                  "Cambia la duración, no el tono. Se aplica en la siguiente lectura, "
                  "sin reiniciar nada."),
    "voz": ("Voz",
            "Voces instaladas del motor y el idioma elegidos.\n\n"
            "• Calidad alta: la más natural (más matices y pausas), 60-110 MB.\n"
            "• Calidad media: muy buena y más ligera, 60-75 MB.\n"
            "• Calidad baja: solo para equipos muy justos; suena metálica.\n"
            "• Todas leen mucho más rápido que el tiempo real: la calidad se paga en "
            "disco, no en espera.\n"
            "• Si una voz no aparece, descárgala con «Instalar voces…»."),
    "instalar": ("Instalar voces",
                 "Descarga voces del repositorio oficial de Piper (60-110 MB cada una). "
                 "Se guardan en la carpeta del lector y aparecen en el desplegable al "
                 "terminar, sin reiniciar."),
    "estado": ("Estado",
               "• GPU: la usan Handy (dictado) y Ollama (IA); el lector nunca. Si aquí "
               "pone «en uso», es por ellos.\n"
               "• Lector: parado (proceso cerrado), en marcha (listo para leer) o "
               "leyendo con la voz indicada."),
    "seleccion": ("Qué leer",
                  "Qué se lee al pulsar Ctrl+Alt+R.\n\n"
                  "• Selección (recomendado): si hay texto seleccionado en la ventana con el "
                  "foco, lee eso; si no hay nada seleccionado, lee el portapapeles.\n"
                  "  – Primero se pregunta a la app por accesibilidad (UI Automation): sin "
                  "tocar nada. Funciona en navegadores, editores y Office.\n"
                  "  – En consolas clásicas (cmd/PowerShell) se lee la selección nativa del "
                  "búfer, también sin portapapeles.\n"
                  "  – Si la app no lo expone (o estás dentro de Escritorio remoto) se usa un "
                  "Ctrl+C temporal y se restaura el portapapeles.\n"
                  "• Portapapeles: lee siempre lo último copiado.\n"
                  "• Aviso: en una terminal, Ctrl+C puede interrumpir el comando; ahí elige "
                  "Portapapeles."),
    "handy": ("Handy (dictado)",
              "Handy es el programa que dicta (Ctrl+Alt+Espacio) y que ejecuta el asistente "
              "con IA (Ctrl+Shift+Espacio).\n\n"
              "• Este panel solo muestra si está abierto y qué modelo y atajos tiene: no lo "
              "abre, no lo cierra y no cambia nada suyo.\n"
              "• Para tocarlo: Handy → Ajustes (Modelos, Micrófono, Atajos)."),
    "handy_modelo": ("Modelo de dictado",
                     "El modelo con el que Handy transcribe tu voz. Por defecto Whisper Turbo "
                     "(large-v3-turbo): rápido y completo también con dictados largos.\n\n"
                     "Se cambia en Handy → Ajustes → Modelos; aquí solo se muestra."),
    "handy_atajos": ("Atajos de Handy",
                     "Los atajos que Handy tiene configurados ahora mismo (se leen de su "
                     "configuración).\n\n"
                     "Si no son los que usas, cámbialos en Handy → Ajustes → Atajos."),
    "gpu": ("GPU",
            "La GPU la usan Handy (Whisper) y Ollama (la IA). El lector con Piper o Kokoro "
            "va en CPU y no la toca.\n\n"
            "Los motores de voz de alta calidad (Chatterbox, XTTS) sí pueden usar la GPU: "
            "por eso, mientras leen, la GPU aparece en uso."),
    "resumen": ("Atajo de resumen",
                "Es el atajo del asistente de Handy (Ctrl+Shift+Espacio).\n\n"
                "Dictas lo que quieras resumir y, al parar, Handy transcribe y Ollama lo "
                "procesa; el resultado se pega donde tengas el cursor y queda copiado en el "
                "portapapeles."),
    "resumen_que": ("Qué hace el resumen",
                    "1) Grabas con Ctrl+Shift+Espacio.\n"
                    "2) Handy transcribe tu voz.\n"
                    "3) Ollama procesa el texto con el prompt de post-procesado activo.\n"
                    "4) El resultado se pega en el cursor y se copia al portapapeles.\n\n"
                    "El mismo atajo sirve para resumir, reescribir o redactar: lo que cambia "
                    "es el prompt elegido en Handy."),
    "resumen_modelo": ("Modelo del resumen",
                       "Modelo de Ollama que usa Handy para resumir. Aquí ves los que tienes "
                       "instalados y los recomendados (★).\n\n"
                       "Al pulsar «Usar», el panel cierra Handy, cambia el modelo en su "
                       "configuración y lo vuelve a abrir (unos segundos). Se guarda una copia "
                       "`settings_store.json.bak-panel` por si acaso.\n\n"
                       "Ojo con los modelos grandes (6 GB o más): con el lector en la GPU puede "
                       "no caber y tardar más."),
    "resumen_prompt": ("Prompt del resumen",
                       "El prompt de post-procesado que tiene Handy activo (por ejemplo, el de "
                       "resumen). Es lo que decide si resume, reescribe o redacta.\n\n"
                       "Se cambia en Handy → Ajustes → Post-procesado; aquí solo se muestra."),
    "resumen_estado": ("Cómo va el resumen",
                       "Si el post-procesado está activado en Handy, el atajo resume; si está "
                       "desactivado, solo transcribe.\n\n"
                       "El modelo vive en la GPU y se descarga solo tras 5 minutos sin usarlo; "
                       "el primer resumen de una tanda tarda un poco más.")
}

_TOOLTIPS = []
_AYUDAS_ABIERTAS = {}
_GUIA = None


def resumen(clave):
    """Primera frase de la ayuda de esa clave (para los tooltips)."""
    _titulo, texto = AYUDAS.get(clave, ("", ""))
    limpio = texto.replace("• ", "").strip()
    frase = limpio.split(". ")[0].strip()
    if frase and not frase.endswith("."):
        frase += "."
    return frase


def _escala(widget):
    try:
        return max(1.0, widget.winfo_fpixels("1i") / 96.0)
    except (tk.TclError, AttributeError):
        return 1.0


def _px(widget, valor):
    return max(1, int(round(valor * _escala(widget))))


def _num(valor):
    """2.4 -> '2,4' (coma decimal, como el resto de la UI)."""
    if valor is None:
        return "?"
    texto = f"{valor:g}" if isinstance(valor, (int, float)) else str(valor)
    return texto.replace(".", ",")


# --- Tooltip ---

class Tooltip:
    """Tooltip clasico de Tk: aparece a los ~500 ms y no roba el foco."""

    def __init__(self, widget, texto, retardo=500):
        self.widget = widget
        self.texto = texto or ""
        self.retardo = retardo
        self._after = None
        self._ventana = None
        try:
            widget.bind("<Enter>", self._entrar, add="+")
            widget.bind("<Leave>", self._salir, add="+")
            widget.bind("<ButtonPress>", self._salir, add="+")
        except tk.TclError:
            pass
        _TOOLTIPS.append(self)

    def _entrar(self, _evento=None):
        self._cancelar()
        try:
            self._after = self.widget.after(self.retardo, self._mostrar)
        except tk.TclError:
            self._after = None

    def _cancelar(self):
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except tk.TclError:
                pass
            self._after = None

    def _mostrar(self):
        self._after = None
        if self._ventana is not None or not self.texto:
            return
        try:
            if not self.widget.winfo_exists():
                return
            ventana = tk.Toplevel(self.widget)
            ventana.wm_overrideredirect(True)
            try:
                ventana.wm_attributes("-topmost", True)
            except tk.TclError:
                pass
            marco = tk.Frame(ventana, bg=TARJETA, highlightbackground=BORDE,
                             highlightthickness=1)
            marco.pack()
            tk.Label(marco, text=self.texto, bg=TARJETA, fg=TEXTO, justify="left",
                     anchor="w", font=(FAMILIA, 9), padx=_px(self.widget, 8),
                     pady=_px(self.widget, 5),
                     wraplength=_px(self.widget, 360)).pack()
            ventana.update_idletasks()
            x = self.widget.winfo_pointerx() + _px(self.widget, 12)
            y = self.widget.winfo_pointery() + _px(self.widget, 18)
            ancho = ventana.winfo_reqwidth()
            alto = ventana.winfo_reqheight()
            x = min(x, self.widget.winfo_screenwidth() - ancho - _px(self.widget, 8))
            if y + alto > self.widget.winfo_screenheight() - _px(self.widget, 8):
                y = self.widget.winfo_pointery() - alto - _px(self.widget, 12)
            ventana.geometry(f"+{max(0, x)}+{max(0, y)}")
            self._ventana = ventana
        except Exception:
            log.exception("No se pudo mostrar el tooltip")
            self._ventana = None

    def ocultar(self):
        self._cancelar()
        if self._ventana is not None:
            try:
                self._ventana.destroy()
            except tk.TclError:
                pass
            self._ventana = None

    def _salir(self, _evento=None):
        self.ocultar()


def ocultar_tooltips():
    for tip in list(_TOOLTIPS):
        try:
            tip.ocultar()
        except Exception:
            log.exception("No se pudo ocultar un tooltip")


# --- Ventana de ayuda ---

def mostrar_ayuda(raiz, clave):
    """Ventana pequena con la ayuda de ``clave``; reusa la que ya este abierta."""
    try:
        datos = AYUDAS.get(clave)
        if not datos:
            return None
        abierta = _AYUDAS_ABIERTAS.get(clave)
        if abierta is not None:
            try:
                if abierta.winfo_exists():
                    abierta.deiconify()
                    abierta.lift()
                    abierta.focus_set()
                    return abierta
            except tk.TclError:
                pass
            _AYUDAS_ABIERTAS.pop(clave, None)

        titulo, texto = datos
        escala = _escala(raiz)
        ventana = tk.Toplevel(raiz)
        _AYUDAS_ABIERTAS[clave] = ventana
        ventana.title(f"Ayuda · {titulo}")
        ventana.configure(bg=FONDO)
        ventana.geometry(f"{round(520 * escala)}x{round(360 * escala)}")
        ventana.resizable(False, False)
        try:
            ventana.transient(raiz)
        except tk.TclError:
            pass

        tk.Label(ventana, text=titulo, bg=FONDO, fg=ACENTO,
                 font=(FAMILIA, 14, "bold")).pack(
                     anchor="w", padx=_px(raiz, 18), pady=(_px(raiz, 16), _px(raiz, 8)))
        tk.Label(ventana, text=texto, bg=FONDO, fg=TEXTO, justify="left", anchor="w",
                 font=(FAMILIA, 10), wraplength=_px(raiz, 484)).pack(
                     fill="x", padx=_px(raiz, 18))
        boton = tk.Button(ventana, text="Cerrar", command=ventana.destroy, bg=TARJETA,
                          fg=TEXTO, activebackground=ACENTO, activeforeground=FONDO,
                          relief="flat", bd=0, highlightthickness=0, cursor="hand2",
                          font=(FAMILIA, 9), padx=_px(raiz, 10), pady=_px(raiz, 4))
        boton.pack(side="bottom", pady=_px(raiz, 14))

        def _olvidar(_evento=None):
            if _AYUDAS_ABIERTAS.get(clave) is ventana:
                _AYUDAS_ABIERTAS.pop(clave, None)

        ventana.bind("<Destroy>", _olvidar)
        return ventana
    except Exception:
        log.exception("No se pudo abrir la ayuda %s", clave)
        return None


# --- Guia comparativa de voces ---

def _marcas(idioma):
    if idioma == "es":
        return {"es_MX-claude-high": " (recomendada)",
                "es_ES-sharvard-medium": " (mejor de España)"}
    return {"en_US-lessac-high": " (recomendada)",
            "en_US-amy-medium": " (la más rápida)"}


def _fila_piper(entrada, marcas):
    """(cabecera, corte de la negrita, nota) de una voz Piper."""
    marca = marcas.get(entrada["id"], "")
    if voces.tamano_mb_instalada(entrada["id"], estado.LECTOR_DIR) is None:
        marca += " (sin instalar)"
    cabecera = (f"{entrada['id']}{marca} — {entrada['acento']}, {entrada['sexo']} — "
                f"{entrada['calidad']} — {entrada['mb']} MB — "
                f"{_num(entrada['carga_s'])} s — {entrada['rtf']}")
    return cabecera, len(entrada["id"]) + len(marca), entrada["nota"]


def _fila_kokoro(idioma):
    info = voces.KOKORO_INFO.get(idioma) or {}
    nombres = ", ".join(info.get("voces") or [])
    cabecera = (f"Kokoro ({nombres}) — {info.get('acento', '')}, {info.get('sexo', '')} — "
                f"{info.get('calidad', '')} — ~{info.get('ram_mb', '?')} MB RAM — "
                f"{_num(info.get('carga_s'))} s — {info.get('rtf', '')}")
    return cabecera, cabecera.index(" — "), info.get("nota", "")


def _insertar(t, texto, etiquetas=()):
    t.insert("end", texto, etiquetas)


def _insertar_bloque(t, cabecera, nota, negrita_hasta):
    """Cabecera con el id en negrita, resto normal; nota pequena en gris."""
    _insertar(t, cabecera[:negrita_hasta], ("b",))
    _insertar(t, cabecera[negrita_hasta:] + "\n")
    if nota:
        _insertar(t, nota + "\n", ("nota",))


def _contenido_guia(t):
    _insertar(t, "¿Qué voz elijo?\n", ("h1",))
    _insertar(t, "Todas las voces de Piper leen en CPU más rápido que el tiempo real: "
                 "la diferencia está en la naturalidad y el acento, no en la espera. "
                 "Los tiempos son medidas reales en este PC.\n")

    _insertar(t, "La respuesta rápida\n", ("h2",))
    for linea in (
        "Más natural: Chatterbox (GPU; acepta pausas entre frases).",
        "Mejor equilibrio calidad/velocidad: es_MX-claude-high (Piper).",
        "Mejor español de España: es_ES-sharvard-medium.",
        "Más ligera y rápida: es_ES-davefx-medium (español) y en_US-amy-medium (inglés).",
        "Inglés: en_US-lessac-high; Kokoro af_heart es la alternativa si quieres un solo motor.",
        "Lo peor: las voces low/x_low (metálicas) y Kokoro en español (plano y ~450 MB).",
    ):
        _insertar(t, f"• {linea}\n")
    _insertar(t, "\n")

    _insertar(t, "Motores: rápido o natural\n", ("h2",))
    for linea in (
        "Piper — CPU · 20-37× más rápido que el tiempo real · 60-110 MB por voz · "
        "el recomendado para leer a diario.",
        "Kokoro — CPU · ~450 MB de RAM · 3,6× · inglés muy bueno, español flojo.",
        "Chatterbox — GPU 3,2 GB · 1,3× (genera más lento de lo que habla) · la más natural; "
        "puede hacer pausas y tarda ~20 s en cargar.",
        "XTTS — GPU 1,8 GB · 1,6× más rápido · 58 voces y 17 idiomas; acento latino.",
        "Orpheus 3B / F5-TTS — no instalados: Orpheus pide ~8 GB de VRAM (no cabe con Handy) "
        "y F5 es lento en español.",
    ):
        _insertar(t, f"• {linea}\n")
    _insertar(t, "\n")

    _insertar(t, "Español\n", ("h2",))
    marcas = _marcas("es")
    for entrada in sorted(voces.CATALOGO.get("es", []), key=lambda e: e.get("orden", 99)):
        cabecera, corte, nota = _fila_piper(entrada, marcas)
        _insertar_bloque(t, cabecera, nota, corte)
    cabecera, corte, nota = _fila_kokoro("es")
    _insertar_bloque(t, cabecera, nota, corte)
    _insertar(t, "\n")

    _insertar(t, "English\n", ("h2",))
    marcas = _marcas("en")
    for entrada in sorted(voces.CATALOGO.get("en", []), key=lambda e: e.get("orden", 99)):
        cabecera, corte, nota = _fila_piper(entrada, marcas)
        _insertar_bloque(t, cabecera, nota, corte)
    cabecera, corte, nota = _fila_kokoro("en")
    _insertar_bloque(t, cabecera, nota, corte)
    _insertar(t, "\n")

    _insertar(t, "Cómo se mide\n", ("h2",))
    _insertar(t, "Velocidad = veces más rápido que el tiempo real al generar el audio "
                 "(medido con la voz ya cargada). Carga = lo que tarda en sonar la "
                 "primera frase tras encender el lector.\n\n")
    _insertar(t, "Piper no tiene voces «high» de España: las de calidad alta en español "
                 "son de México y Argentina.", ("nota",))


def _rueda(texto, evento):
    try:
        if getattr(evento, "num", None) == 4:  # Linux: rueda arriba
            texto.yview_scroll(-3, "units")
        elif getattr(evento, "num", None) == 5:
            texto.yview_scroll(3, "units")
        else:
            paso = -1 if evento.delta > 0 else 1
            texto.yview_scroll(paso * 3, "units")
    except tk.TclError:
        pass
    return "break"


def mostrar_guia(raiz):
    """Guia «¿Qué elijo?»: comparativa de voces en un Text de solo lectura."""
    global _GUIA
    try:
        if _GUIA is not None:
            try:
                if _GUIA.winfo_exists():
                    _GUIA.deiconify()
                    _GUIA.lift()
                    _GUIA.focus_set()
                    return _GUIA
            except tk.TclError:
                pass
            _GUIA = None

        escala = _escala(raiz)
        ventana = tk.Toplevel(raiz)
        _GUIA = ventana
        ventana.title("¿Qué voz elijo?")
        ventana.configure(bg=FONDO)
        ventana.geometry(f"{round(600 * escala)}x{round(560 * escala)}")
        try:
            ventana.transient(raiz)
        except tk.TclError:
            pass

        estilo = ttk.Style(ventana)
        try:
            estilo.configure("Guia.Vertical.TScrollbar", background=TARJETA,
                             troughcolor=FONDO, bordercolor=FONDO, arrowcolor=GRIS,
                             lightcolor=TARJETA, darkcolor=TARJETA)
        except tk.TclError:
            pass

        contenedor = tk.Frame(ventana, bg=FONDO)
        contenedor.pack(fill="both", expand=True, padx=_px(raiz, 14),
                        pady=_px(raiz, 12))
        texto = tk.Text(contenedor, wrap="word", bg=FONDO, fg=TEXTO, bd=0,
                        highlightthickness=0, padx=_px(raiz, 6), pady=_px(raiz, 4),
                        font=(FAMILIA, 10), cursor="arrow", spacing1=2, spacing3=2)
        barra = ttk.Scrollbar(contenedor, orient="vertical", command=texto.yview,
                              style="Guia.Vertical.TScrollbar")
        texto.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        texto.pack(side="left", fill="both", expand=True)

        texto.tag_configure("h1", font=(FAMILIA, 16, "bold"), foreground=ACENTO,
                            spacing1=_px(raiz, 4), spacing3=_px(raiz, 8))
        texto.tag_configure("h2", font=(FAMILIA, 12, "bold"), foreground=TEXTO,
                            spacing1=_px(raiz, 14), spacing3=_px(raiz, 6))
        texto.tag_configure("b", font=(FAMILIA, 10, "bold"))
        texto.tag_configure("nota", font=(FAMILIA, 8), foreground=GRIS)

        _contenido_guia(texto)
        texto.configure(state="disabled")
        texto.yview_moveto(0)
        texto.bind("<MouseWheel>", lambda e: _rueda(texto, e))
        texto.bind("<Button-4>", lambda e: _rueda(texto, e))
        texto.bind("<Button-5>", lambda e: _rueda(texto, e))
        ventana.bind("<MouseWheel>", lambda e: _rueda(texto, e))

        def _olvidar(_evento=None):
            global _GUIA
            if _GUIA is ventana:
                _GUIA = None

        ventana.bind("<Destroy>", _olvidar)
        return ventana
    except Exception:
        log.exception("No se pudo abrir la guia de voces")
        return None


def cerrar_todas():
    """Cierra ayudas, guia y tooltips (al ocultar o salir del panel)."""
    global _GUIA
    ocultar_tooltips()
    for clave, ventana in list(_AYUDAS_ABIERTAS.items()):
        try:
            ventana.destroy()
        except tk.TclError:
            pass
        _AYUDAS_ABIERTAS.pop(clave, None)
    if _GUIA is not None:
        try:
            _GUIA.destroy()
        except tk.TclError:
            pass
        _GUIA = None
