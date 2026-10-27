"""Panel de voz - Asistente de voz local (spec 07).

Ventana Tk + icono en la bandeja para manejar el lector sin tocar Handy:
modo Lectura/Dictado, encender/apagar el lector, idioma, motor y voz, e instalar
voces Piper. Todo cambio se persiste al momento (``estado.json`` / ``lector.json``)
y las acciones lentas van en hilos para no bloquear la UI.

Uso:
  panel.py            abre el panel (pythonw, sin consola)
  panel.py --simular  no toca Handy/Ollama/lector (solo pruebas de UI)
"""

import argparse
import logging
import os
import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

DIR = Path(__file__).resolve().parent
ES_WINDOWS = sys.platform == "win32"

# pythonw arranca sin stdout/stderr: se les da un destino valido antes de todo
if sys.stdout is None or sys.stderr is None:
    _nulo = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stdout or _nulo
    sys.stderr = sys.stderr or _nulo


def _base_sistema():
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(local) / "asistente-voz-local"
    datos = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(datos) / "asistente-voz-local"


# Con el pythonw base (arranque automatico) hay que usar las librerias del venv del lector
if ES_WINDOWS and sys.prefix == sys.base_prefix:
    _VENV_LIBS = _base_sistema() / "lector" / ".venv" / "Lib" / "site-packages"
    if _VENV_LIBS.is_dir():
        import site
        site.addsitedir(str(_VENV_LIBS))

try:
    from . import ayuda, control, estado, icono, toast, voces
except ImportError:  # lanzado como script (pythonw panel/panel.py)
    sys.path.insert(0, str(DIR))
    import ayuda
    import control
    import estado
    import icono
    import toast
    import voces

log = logging.getLogger("panel")

# Tema oscuro como la pildora de Handy
FONDO = "#2c2b29"
TARJETA = "#3a3936"
TEXTO = "#fbfbfb"
GRIS = "#a3a09a"
ACENTO = "#f28cbb"
FAMILIA = "Segoe UI" if ES_WINDOWS else "DejaVu Sans"

_CANDADO = None  # mutex/flock de instancia unica (se mantiene vivo todo el proceso)

IDIOMAS = {"es": "Español", "en": "English"}
MOTORES = {"piper": "Piper", "kokoro": "Kokoro", "chatterbox": "Chatterbox", "xtts": "XTTS"}
VELOCIDADES = {"lenta": 0.9, "normal": 1.0, "rapida": 1.1}
ETIQUETAS_VELOCIDAD = {"lenta": "Lenta", "normal": "Normal", "rapida": "Rápida"}


def _parsear_atajo(atajo):
    """'ctrl+alt+p' -> (mods, vk) con los valores de RegisterHotKey, o None."""
    mods = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}
    teclas = {"space": 0x20, "espacio": 0x20, "enter": 0x0D, "tab": 0x09}
    mod, vk = 0x4000, None  # MOD_NOREPEAT
    for parte in (atajo or "").lower().split("+"):
        if parte in mods:
            mod |= mods[parte]
        elif parte in teclas:
            vk = teclas[parte]
        elif re.fullmatch(r"f([1-9]|1[0-2])", parte):
            vk = 0x6F + int(parte[1:])
        elif len(parte) == 1 and parte.isalnum():
            vk = ord(parte.upper())
    return (mod, vk) if vk is not None else None


class Panel:
    """Ventana principal, icono de bandeja y atajo global."""

    def __init__(self, raiz):
        self.raiz = raiz
        self.cfg = estado.leer_lector_json()
        self.cfg_panel = estado.cargar_panel_json()
        self.estado = estado.leer_estado()
        self.hay_gpu = control.gpu_disponible()
        self.motor_rec = voces.motor_recomendado(self.hay_gpu)
        self.ocupado = False
        self.cerrando = False
        self.icono = None
        self._ventana_voces = None
        self._filas_voces = {}
        self._progreso_voces = None
        self._voces_lista = []
        self._voces_etiquetas = []
        self._gpu_texto = "GPU: comprobando…"
        self._gpu_ultimo = 0.0
        self._gpu_hilo = None
        self._handy_en_marcha = None
        self._modelos = []
        self._modelos_hilo = None
        self._atajo_r_hilo = None
        self._atajo_r_id = None
        self._controles = []

        self._configurar_ventana()
        self._construir()
        self._actualizar_todo()

    # --- Ventana ---

    def _configurar_ventana(self):
        self.raiz.title("Panel de voz")
        # 460x520 en pantallas al 100 % como maximo; escalado en pantallas con DPI alto
        self.escala = max(1.0, self.raiz.winfo_fpixels("1i") / 96.0)
        self.raiz.geometry(f"{round(460 * self.escala)}x{round(520 * self.escala)}")
        self.raiz.resizable(False, False)
        self.raiz.configure(bg=FONDO)
        self.raiz.protocol("WM_DELETE_WINDOW", self.ocultar)
        self.raiz.option_add("*TCombobox*Listbox.background", TARJETA)
        self.raiz.option_add("*TCombobox*Listbox.foreground", TEXTO)
        self.raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
        self.raiz.option_add("*TCombobox*Listbox.selectForeground", FONDO)

        estilo = ttk.Style(self.raiz)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Voz.TCombobox", fieldbackground=TARJETA, background=TARJETA,
                         foreground=TEXTO, arrowcolor=TEXTO, bordercolor=TARJETA,
                         lightcolor=TARJETA, darkcolor=TARJETA, padding=3)
        estilo.map("Voz.TCombobox", fieldbackground=[("readonly", TARJETA)],
                   foreground=[("readonly", TEXTO)], selectbackground=[("readonly", TARJETA)],
                   selectforeground=[("readonly", TEXTO)])
        estilo.map("Voz.TCombobox", background=[("disabled", TARJETA)],
                   foreground=[("disabled", GRIS)])

    def _px(self, valor):
        """Pixeles logicos -> reales segun el DPI de la pantalla."""
        return max(1, int(round(valor * self.escala)))

    def _seccion(self, titulo, clave=None, padre=None):
        """Cabecera de seccion + «?» escondido con su ayuda y tooltip."""
        padre = padre or self.raiz
        caja = tk.Frame(padre, bg=FONDO)
        caja.pack(fill="x", padx=self._px(12), pady=(self._px(7), 0))
        cabecera = tk.Frame(caja, bg=FONDO)
        cabecera.pack(fill="x")
        etiqueta = tk.Label(cabecera, text=titulo.upper(), bg=FONDO, fg=GRIS,
                            font=(FAMILIA, 8, "bold"))
        etiqueta.pack(side="left")
        if clave:
            resumen = ayuda.resumen(clave)
            boton = tk.Button(cabecera, text="?", command=lambda c=clave: ayuda.mostrar_ayuda(
                                  self.raiz, c), bg=FONDO, fg=ACENTO, activebackground=FONDO,
                              activeforeground=TEXTO, relief="flat", bd=0,
                              highlightthickness=0, cursor="hand2", width=1,
                              font=(FAMILIA, 8, "bold"), padx=self._px(2), pady=0)
            boton.pack(side="right")
            ayuda.Tooltip(boton, resumen)
            ayuda.Tooltip(etiqueta, resumen)
        fila = tk.Frame(caja, bg=FONDO)
        fila.pack(fill="x", pady=(self._px(2), 0))
        return fila

    def _boton(self, padre, texto, comando, ancho=10):
        b = tk.Button(padre, text=texto, command=comando, width=ancho,
                      bg=TARJETA, fg=TEXTO, activebackground=ACENTO, activeforeground=FONDO,
                      relief="flat", bd=0, highlightthickness=0, cursor="hand2",
                      font=(FAMILIA, 9), padx=self._px(4), pady=self._px(4))
        self._controles.append(b)
        return b

    def _construir(self):
        tk.Label(self.raiz, text="Panel de voz", bg=FONDO, fg=TEXTO,
                 font=(FAMILIA, 15, "bold")).pack(pady=(self._px(12), 0))
        tk.Label(self.raiz, text="Lector y dictado locales · la voz de calidad usa la GPU",
                 bg=FONDO, fg=GRIS, font=(FAMILIA, 9)).pack(pady=(0, self._px(4)))

        estilo = ttk.Style(self.raiz)
        try:
            estilo.configure("Panel.TNotebook", background=FONDO, borderwidth=0,
                             tabmargins=(self._px(6), self._px(4), self._px(6), 0))
            estilo.configure("Panel.TNotebook.Tab", background=TARJETA, foreground=GRIS,
                             padding=(self._px(12), self._px(5)), borderwidth=0,
                             font=(FAMILIA, 9, "bold"))
            estilo.map("Panel.TNotebook.Tab",
                       background=[("selected", ACENTO)], foreground=[("selected", FONDO)])
        except tk.TclError:
            pass

        self.notebook = ttk.Notebook(self.raiz, style="Panel.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=self._px(8), pady=(0, 0))
        self.tab_lector = tk.Frame(self.notebook, bg=FONDO)
        self.tab_dictado = tk.Frame(self.notebook, bg=FONDO)
        self.tab_resumen = tk.Frame(self.notebook, bg=FONDO)
        self.notebook.add(self.tab_lector, text="Lector de voz")
        self.notebook.add(self.tab_dictado, text="Dictado (Handy)")
        self.notebook.add(self.tab_resumen, text="Resumen")
        self._construir_lector()
        self._construir_dictado()
        self._construir_resumen()

        self.l_mensaje = tk.Label(self.raiz, text="", bg=FONDO, fg=GRIS, font=(FAMILIA, 9),
                                  anchor="w", justify="left", wraplength=self._px(400))
        self.l_mensaje.pack(fill="x", padx=self._px(16), pady=(self._px(4), 0))

        tk.Label(self.raiz,
                 text="Lee: Ctrl+Alt+R · Dicta: Ctrl+Alt+Espacio\n"
                      "Resume: Ctrl+Shift+Espacio · Panel: Ctrl+Alt+P",
                 bg=FONDO, fg=GRIS, font=(FAMILIA, 8), justify="center").pack(
                     side="bottom", pady=(0, self._px(6)))
        self._ajustar_ventana()

    # --- Pestaña: lector de voz ---

    def _construir_lector(self):
        padre = self.tab_lector

        fila = self._seccion("Lector de voz", "lector", padre)
        self.b_lector = self._boton(fila, "Apagado", self._alternar_lector, ancho=11)
        self.b_lector.pack(side="left", padx=(0, self._px(8)))
        ayuda.Tooltip(self.b_lector, "Enciende o apaga el lector.")
        self.l_lector = tk.Label(fila, text="parado", bg=FONDO, fg=GRIS, font=(FAMILIA, 9))
        self.l_lector.pack(side="left")

        fila = self._seccion("Idioma", "idioma", padre)
        self.b_idioma = {}
        for clave, etiqueta in IDIOMAS.items():
            b = self._boton(fila, etiqueta, lambda c=clave: self.poner_idioma(c), ancho=11)
            b.pack(side="left", padx=(0, self._px(6)))
            ayuda.Tooltip(b, "Cambia la pronunciación (no traduce).")
            self.b_idioma[clave] = b

        fila = self._seccion("Motor", "motor", padre)
        self.b_motor = {}
        for clave, etiqueta in MOTORES.items():
            texto = f"★ {etiqueta}" if clave == self.motor_rec else etiqueta
            b = self._boton(fila, texto, lambda c=clave: self.poner_motor(c), ancho=10)
            b.pack(side="left", padx=(0, self._px(4)))
            ayuda.Tooltip(b, "Piper/Kokoro: rápidos y en CPU. Chatterbox/XTTS: más naturales, GPU.")
            self.b_motor[clave] = b

        nombre_rec, motivo = voces.RECOMENDACION_MOTOR.get(
            self.motor_rec, voces.RECOMENDACION_MOTOR["piper"])
        self.l_recomendacion = tk.Label(padre, text=f"★ Recomendado: {nombre_rec} — {motivo}",
                                        bg=FONDO, fg=ACENTO, font=(FAMILIA, 8), anchor="w",
                                        justify="left", wraplength=self._px(390))
        self.l_recomendacion.pack(fill="x", padx=self._px(14), pady=(self._px(3), 0))

        fila = self._seccion("Velocidad", "velocidad", padre)
        self.b_velocidad = {}
        for clave, etiqueta in ETIQUETAS_VELOCIDAD.items():
            b = self._boton(fila, etiqueta, lambda c=clave: self.poner_velocidad(c), ancho=11)
            b.pack(side="left", padx=(0, self._px(6)))
            ayuda.Tooltip(b, "Ritmo de lectura; cambia la duración, no el tono.")
            self.b_velocidad[clave] = b

        fila = self._seccion("Voz", "voz", padre)
        self.var_voz = tk.StringVar()
        self.combo = ttk.Combobox(fila, textvariable=self.var_voz, state="readonly",
                                  style="Voz.TCombobox", width=20, font=(FAMILIA, 9))
        self.combo.pack(side="left", padx=(0, self._px(5)))
        self.combo.bind("<<ComboboxSelected>>", self._voz_elegida)
        ayuda.Tooltip(self.combo, "Voces instaladas del motor y el idioma elegidos.")
        self._controles.append(self.combo)
        b = self._boton(fila, "Instalar…", self.abrir_instalador, ancho=9)
        b.pack(side="left")
        ayuda.Tooltip(b, "Descarga voces de Piper (60-110 MB cada una).")
        b = self._boton(fila, "¿Qué elijo?", lambda: ayuda.mostrar_guia(self.raiz), ancho=11)
        b.pack(side="left", padx=(self._px(5), 0))
        ayuda.Tooltip(b, "Compara las voces y dice cuál elegir.")

        self.l_voz_info = tk.Label(self.tab_lector, text="", bg=FONDO, fg=GRIS,
                                   font=(FAMILIA, 8), anchor="w", justify="left",
                                   wraplength=self._px(390))
        self.l_voz_info.pack(fill="x", padx=self._px(14), pady=(self._px(3), 0))

        fila = self._seccion("Estado del lector", "estado", padre)
        self.l_estado_lector = tk.Label(fila, text="", bg=FONDO, fg=GRIS,
                                        font=(FAMILIA, 9), anchor="w", justify="left",
                                        wraplength=self._px(390))
        self.l_estado_lector.pack(fill="x")

    # --- Pestaña: dictado y asistente (Handy) ---

    def _construir_dictado(self):
        padre = self.tab_dictado

        fila = self._seccion("Handy", "handy", padre)
        self.l_handy = tk.Label(fila, text="comprobando…", bg=FONDO, fg=GRIS,
                                font=(FAMILIA, 9), anchor="w")
        self.l_handy.pack(fill="x")

        fila = self._seccion("Modelo de dictado", "handy_modelo", padre)
        self.l_modelo_dictado = tk.Label(fila, text="—", bg=FONDO, fg=GRIS,
                                         font=(FAMILIA, 9), anchor="w")
        self.l_modelo_dictado.pack(fill="x")

        fila = self._seccion("Atajos de Handy", "handy_atajos", padre)
        self.l_atajos = tk.Label(fila, text="—", bg=FONDO, fg=GRIS, font=(FAMILIA, 9),
                                 anchor="w", justify="left", wraplength=self._px(390))
        self.l_atajos.pack(fill="x")

        fila = self._seccion("GPU", "gpu", padre)
        self.l_gpu = tk.Label(fila, text=self._gpu_texto, bg=FONDO, fg=GRIS,
                              font=(FAMILIA, 9), anchor="w")
        self.l_gpu.pack(fill="x")

        tk.Label(padre, text="El dictado y el asistente se configuran en Handy "
                             "(Ajustes → Modelos, micrófono y atajos). Este panel solo "
                             "muestra su estado: no cambia nada de Handy.",
                 bg=FONDO, fg=GRIS, font=(FAMILIA, 8), anchor="w", justify="left",
                 wraplength=self._px(390)).pack(fill="x", padx=self._px(14),
                                                pady=(self._px(10), 0))

    # --- Pestaña: resumen (asistente con IA) ---

    def _construir_resumen(self):
        padre = self.tab_resumen
        fila = self._seccion("Atajo de resumen", "resumen", padre)
        self.l_resumen_atajo = tk.Label(fila, text="—", bg=FONDO, fg=TEXTO,
                                        font=(FAMILIA, 12, "bold"), anchor="w")
        self.l_resumen_atajo.pack(fill="x")

        fila = self._seccion("Qué hace", "resumen_que", padre)
        self.l_resumen_que = tk.Label(
            fila, text="Dictas lo que quieras resumir y, al parar, Handy transcribe y "
                       "Ollama lo resume con el prompt activo. El resultado se pega en el "
                       "cursor y queda copiado en el portapapeles.",
            bg=FONDO, fg=GRIS, font=(FAMILIA, 9), anchor="w", justify="left",
            wraplength=self._px(390))
        self.l_resumen_que.pack(fill="x")

        fila = self._seccion("Modelo de resumen", "resumen_modelo", padre)
        self.var_modelo = tk.StringVar()
        self.cmb_modelo = ttk.Combobox(fila, textvariable=self.var_modelo, state="readonly",
                                       style="Voz.TCombobox", width=27, font=(FAMILIA, 9))
        self.cmb_modelo.pack(side="left", padx=(0, self._px(5)))
        self.cmb_modelo.bind("<<ComboboxSelected>>", lambda _e: self._nota_modelo())
        self._controles.append(self.cmb_modelo)
        b = self._boton(fila, "Usar", self.poner_modelo_resumen, ancho=8)
        b.pack(side="left")
        ayuda.Tooltip(b, "Cambia el modelo de Ollama del resumen (reinicia Handy unos segundos).")
        self.l_modelo_nota = tk.Label(padre, text="", bg=FONDO, fg=GRIS, font=(FAMILIA, 8),
                                      anchor="w", justify="left", wraplength=self._px(390))
        self.l_modelo_nota.pack(fill="x", padx=self._px(14), pady=(self._px(3), 0))

        fila = self._seccion("Prompt", "resumen_prompt", padre)
        self.l_resumen_prompt = tk.Label(fila, text="—", bg=FONDO, fg=GRIS,
                                         font=(FAMILIA, 9), anchor="w", justify="left",
                                         wraplength=self._px(390))
        self.l_resumen_prompt.pack(fill="x")

        fila = self._seccion("Cómo va", "resumen_estado", padre)
        self.l_resumen_estado = tk.Label(fila, text="—", bg=FONDO, fg=GRIS,
                                         font=(FAMILIA, 9), anchor="w", justify="left",
                                         wraplength=self._px(390))
        self.l_resumen_estado.pack(fill="x")

        tk.Label(padre, text="El modelo se puede cambiar aquí (se reinicia Handy unos "
                             "segundos). El prompt y el resto se configuran en Handy → "
                             "Ajustes → Post-procesado. El resumen usa la GPU de Ollama.",
                 bg=FONDO, fg=GRIS, font=(FAMILIA, 8), anchor="w", justify="left",
                 wraplength=self._px(390)).pack(fill="x", padx=self._px(14),
                                                pady=(self._px(10), 0))
        self._cargar_modelos()

    # --- Modelo del resumen ---

    def _cargar_modelos(self):
        """Lista de modelos de Ollama en un hilo (ollama list tarda un poco)."""
        if self._modelos_hilo is not None and self._modelos_hilo.is_alive():
            return

        def trabajo():
            try:
                modelos = control.modelos_ollama(recargar=True)
            except Exception:
                log.exception("No se pudieron listar los modelos de Ollama")
                modelos = []
            try:
                self.raiz.after(0, self._poner_modelos, modelos)
            except (tk.TclError, RuntimeError):
                pass

        self._modelos_hilo = threading.Thread(target=trabajo, daemon=True)
        self._modelos_hilo.start()

    def _poner_modelos(self, modelos):
        self._modelos = modelos or []
        nombres = [m["nombre"] for m in self._modelos]
        self.cmb_modelo.configure(values=nombres)
        ajustes = estado.leer_handy_settings() or {}
        activo = ajustes.get("modelo_resumen") or ""
        if activo in nombres:
            self.var_modelo.set(activo)
        elif nombres and not self.var_modelo.get():
            self.var_modelo.set(nombres[0])
        self._nota_modelo()

    def _nota_modelo(self):
        nombre = (self.var_modelo.get() or "").strip()
        entrada = next((m for m in self._modelos if m["nombre"] == nombre), {})
        mb = entrada.get("mb") or 0
        tam = f"{mb/1024:.1f} GB" if mb >= 1024 else (f"{mb} MB" if mb else "")
        partes = [p for p in (entrada.get("nota"), tam) if p]
        try:
            self.l_modelo_nota.configure(text=" · ".join(partes))
        except tk.TclError:
            pass

    def poner_modelo_resumen(self):
        modelo = (self.var_modelo.get() or "").strip()
        if not modelo:
            self._mensaje("Elige un modelo de la lista", error=True)
            return
        self._accion(f"Resumen con {modelo}: cerrando Handy y aplicándolo…",
                     lambda: control.cambiar_modelo_resumen(modelo))

    def _ajustar_ventana(self):
        """Alto justo para el contenido (+ margen), con 640 logicos como tope."""
        try:
            self.raiz.update_idletasks()
            requerido = self.raiz.winfo_reqheight() / self.escala
            alto = min(640.0, max(560.0, requerido + 24))
            self.raiz.geometry(f"{round(460 * self.escala)}x{round(alto * self.escala)}")
        except tk.TclError:
            pass

    # --- Acciones de UI (las llaman los botones y la bandeja) ---

    def _alternar_lector(self):
        self.poner_lector(not self.estado.get("lector"))

    def poner_lector(self, encendido):
        encendido = bool(encendido)
        if self.ocupado:
            self._mensaje("Espera a que termine la acción anterior", error=True)
            return
        self.estado = estado.guardar_estado(lector=encendido)
        self._actualizar_todo()
        self._refrescar_icono()
        if encendido:
            self._liberar_atajo_r()  # el atajo pasa a ser del lector
            self._accion("Arrancando el lector…", control.arrancar_lector)
        else:
            self._accion("Apagando el lector…", self._apagar_y_avisar)

    def _apagar_y_avisar(self):
        """Apaga el lector y se queda él con Ctrl+Alt+R para avisar de que está apagado."""
        resultado = control.apagar_lector()
        if resultado.ok:
            self._registrar_atajo_r()
        return resultado

    # --- Aviso cuando el lector está apagado ---

    def _registrar_atajo_r(self):
        """Mientras el lector está apagado, el panel escucha Ctrl+Alt+R para avisar."""
        if self._atajo_r_hilo is not None:
            return

        def escuchar():
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            mod = 0x1 | 0x2 | 0x4000  # ALT | CONTROL | MOD_NOREPEAT
            if not user32.RegisterHotKey(None, 4, mod, 0x52):  # R
                log.info("Ctrl+Alt+R ocupado: no puedo avisar de que el lector está apagado")
                return
            self._atajo_r_id = ctypes.windll.kernel32.GetCurrentThreadId()
            msg = wintypes.MSG()
            try:
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    if msg.message == 0x0312:  # WM_HOTKEY
                        try:
                            self.raiz.after(0, self._avisar_apagado)
                        except (tk.TclError, RuntimeError):
                            pass
            finally:
                user32.UnregisterHotKey(None, 4)
                self._atajo_r_id = None

        self._atajo_r_hilo = threading.Thread(target=escuchar, daemon=True)
        self._atajo_r_hilo.start()

    def _avisar_apagado(self):
        toast.mostrar(self.raiz, "Lector apagado.\nEnciéndelo en el panel (Ctrl+Alt+P).", 3.5)

    def _liberar_atajo_r(self):
        """Suelta Ctrl+Alt+R (antes de arrancar el lector, que lo registra él)."""
        if self._atajo_r_hilo is None:
            return
        try:
            import ctypes
            if self._atajo_r_id:
                ctypes.windll.user32.PostThreadMessageW(self._atajo_r_id, 0x0012, 0, 0)  # WM_QUIT
        except Exception:
            pass
        self._atajo_r_hilo.join(1.0)
        self._atajo_r_hilo = None

    def poner_idioma(self, idioma):
        if idioma not in IDIOMAS:
            return
        anterior = self.cfg.get("idioma") or "es"
        self.cfg["idioma"] = idioma
        bloque = self._bloque_voz(crear=True)
        disponibles = voces.instaladas(estado.LECTOR_DIR, bloque.get("motor"), idioma)
        if disponibles:
            if bloque.get("voz") not in disponibles:
                bloque["voz"] = disponibles[0]
            self._mensaje(f"Idioma: {IDIOMAS[idioma]}")
            self.cfg_panel["idioma_voz"] = idioma
            estado.guardar_panel_json(self.cfg_panel)
        else:
            # Sin voces en ese idioma no se cambia nada: el lector se quedaria mudo
            self.cfg["idioma"] = anterior
            self._mensaje(f"No hay voces en {IDIOMAS[idioma]}: usa Instalar voces…", error=True)
        estado.guardar_lector_json(self.cfg)
        self._actualizar_todo()

    def poner_motor(self, motor):
        if motor not in MOTORES:
            return
        bloque = self._bloque_voz(crear=True)
        anterior = bloque.get("motor") or "piper"
        bloque["motor"] = motor
        disponibles = voces.instaladas(estado.LECTOR_DIR, motor, self.cfg.get("idioma") or "es")
        if disponibles:
            if bloque.get("voz") not in disponibles:
                bloque["voz"] = disponibles[0]
            self._mensaje(f"Motor: {MOTORES[motor]}")
        else:
            # Sin voces de ese motor no se cambia nada (la voz guardada no serviria)
            bloque["motor"] = anterior
            self._mensaje(f"No hay voces de {MOTORES[motor]} instaladas: usa Instalar voces…",
                          error=True)
        estado.guardar_lector_json(self.cfg)
        self._actualizar_todo()

    def poner_velocidad(self, clave):
        if clave not in VELOCIDADES:
            return
        self.cfg["velocidad"] = VELOCIDADES[clave]
        estado.guardar_lector_json(self.cfg)
        self._mensaje(f"Velocidad: {ETIQUETAS_VELOCIDAD[clave]}")
        self._actualizar_todo()

    def poner_voz(self, nombre):
        nombre = self._sin_estrella(nombre)
        if not nombre:
            return
        bloque = self._bloque_voz(crear=True)
        bloque["voz"] = nombre
        estado.guardar_lector_json(self.cfg)
        self._mensaje(f"Voz: {nombre}")
        self._actualizar_voz_info(nombre=nombre)

    def _voz_elegida(self, _evento=None):
        self.poner_voz(self._sin_estrella(self.var_voz.get()))

    def _bloque_voz(self, crear=False):
        idioma = self.cfg.get("idioma") or "es"
        voces_cfg = self.cfg.get("voces")
        if not isinstance(voces_cfg, dict):
            voces_cfg = self.cfg["voces"] = {}
        bloque = voces_cfg.get(idioma)
        if not isinstance(bloque, dict):
            if not crear:
                return {}
            bloque = {"motor": "piper", "voz": ""}
            voces_cfg[idioma] = bloque
        bloque.setdefault("motor", "piper")
        bloque.setdefault("voz", "")
        return bloque

    # --- Estado de la UI ---

    def _accion(self, mensaje, funcion):
        """Lanza una accion lenta en un hilo; botones deshabilitados mientras."""
        if self.ocupado:
            self._mensaje("Espera a que termine la acción anterior", error=True)
            return
        self.ocupado = True
        self._mensaje(mensaje)
        self._habilitar(False)

        def trabajo():
            try:
                resultado = funcion()
            except Exception as e:
                log.exception("Accion fallida (%s)", mensaje)
                resultado = control.Resultado(False, f"Error: {e}")
            try:
                self.raiz.after(0, self._fin_accion, resultado)
            except (tk.TclError, RuntimeError):
                pass  # la ventana ya se cerro

        threading.Thread(target=trabajo, daemon=True).start()

    def _fin_accion(self, resultado):
        self.ocupado = False
        self._habilitar(True)
        if resultado is not None:
            self._mensaje(resultado.mensaje, error=not resultado.ok)
        self._actualizar_todo()
        self._refrescar_icono()

    def _habilitar(self, activo):
        estado_boton = "normal" if activo else "disabled"
        for control_ in self._controles:
            try:
                control_.configure(state=estado_boton)
            except tk.TclError:
                pass
        try:
            self.combo.configure(state="readonly" if activo else "disabled")
        except tk.TclError:
            pass

    def _mensaje(self, texto, error=False):
        self.l_mensaje.configure(text=texto or "", fg=ACENTO if error else GRIS)

    def _pintar_grupo(self, grupo, elegido):
        for clave, boton in grupo.items():
            activo = clave == elegido
            boton.configure(bg=ACENTO if activo else TARJETA,
                            fg=FONDO if activo else TEXTO,
                            activebackground=ACENTO, activeforeground=FONDO)

    def _actualizar_todo(self):
        encendido = bool(self.estado.get("lector"))
        self.b_lector.configure(text="Encendido" if encendido else "Apagado",
                                bg=ACENTO if encendido else TARJETA,
                                fg=FONDO if encendido else TEXTO)
        self._actualizar_lector_linea()

        idioma = self.cfg.get("idioma") or "es"
        self._pintar_grupo(self.b_idioma, idioma)
        bloque = self._bloque_voz()
        motor = bloque.get("motor") or "piper"
        self._pintar_grupo(self.b_motor, motor)
        velocidad = float(self.cfg.get("velocidad") or 1.0)
        clave_velocidad = min(VELOCIDADES, key=lambda c: abs(VELOCIDADES[c] - velocidad))
        self._pintar_grupo(self.b_velocidad, clave_velocidad)
        self._actualizar_voces(idioma, motor, bloque.get("voz"))
        self._actualizar_voz_info(idioma, motor, self._sin_estrella(self.var_voz.get()))
        self.l_gpu.configure(text=self._gpu_texto)
        self._actualizar_dictado()

    def _actualizar_dictado(self):
        """Pestaña de Handy: estado, modelo y atajos (solo lectura)."""
        try:
            ajustes = estado.leer_handy_settings()
        except Exception:
            ajustes = None
        if ajustes is None:
            self.l_handy.configure(text="Handy: no encuentro su configuración")
            self.l_modelo_dictado.configure(text="—")
            self.l_atajos.configure(text="—")
            for etiqueta, texto in ((self.l_resumen_atajo, "—"),
                                    (self.l_resumen_modelo, "—"),
                                    (self.l_resumen_estado, "No encuentro la configuración de Handy.")):
                try:
                    etiqueta.configure(text=texto)
                except tk.TclError:
                    pass
            return
        en_marcha = getattr(self, "_handy_en_marcha", None)
        if en_marcha is None:
            texto_handy = "Handy: comprobando…"
        else:
            texto_handy = "Handy: en marcha" if en_marcha else "Handy: cerrado"
        self.l_handy.configure(text=texto_handy)
        self.l_modelo_dictado.configure(text=f"{ajustes['modelo']} · idioma {ajustes['idioma'] or '?'}")
        atajos = []
        if ajustes["atajo_dictado"]:
            atajos.append(f"Dictar: {ajustes['atajo_dictado']}")
        if ajustes["atajo_asistente"]:
            atajos.append(f"Asistente: {ajustes['atajo_asistente']}")
        self.l_atajos.configure(text="\n".join(atajos) or "—")

        activo = "activado" if ajustes.get("resumen_activo") else "desactivado"
        self.l_resumen_atajo.configure(text=ajustes.get("atajo_resumen") or "—")
        self.l_resumen_prompt.configure(text=f"Prompt activo: {ajustes.get('prompt_resumen')}")
        if not self.var_modelo.get() and ajustes.get("modelo_resumen"):
            self.var_modelo.set(ajustes.get("modelo_resumen"))
        self._nota_modelo()
        self.l_resumen_estado.configure(
            text=f"Post-procesado {activo} en Handy. El resumen usa la GPU (Ollama) y "
                 f"tarda unos segundos en el primer uso.")

    def _actualizar_voz_info(self, idioma=None, motor=None, nombre=None):
        idioma = idioma or (self.cfg.get("idioma") or "es")
        if motor is None:
            motor = self._bloque_voz().get("motor") or "piper"
        if nombre is None:
            nombre = self.var_voz.get()
        try:
            self.l_voz_info.configure(text=self._texto_voz_info(idioma, motor, nombre))
        except tk.TclError:
            pass

    def _texto_voz_info(self, idioma, motor, nombre):
        """«Calidad alta · México · 60 MB · 37× tiempo real» o la version del motor."""
        motor = (motor or "piper").lower()
        if motor == "kokoro":
            info = voces.KOKORO_INFO.get(idioma) or {}
            if info:
                etiqueta = "español limitado" if idioma == "es" else "inglés, su punto fuerte"
                rtf = (info.get("rtf") or "").split(" ")[0]
                partes = ["Kokoro", etiqueta]
                if info.get("ram_mb"):
                    partes.append(f"~{info['ram_mb']} MB")
                if rtf:
                    partes.append(rtf)
                return " · ".join(partes)
        if motor in voces.INFO_CALIDAD:
            info = voces.INFO_CALIDAD[motor]
            nombre_motor = "Chatterbox" if motor == "chatterbox" else "XTTS"
            return (f"{nombre_motor} · alta calidad · GPU {info['vram_gb']:g} GB · "
                    f"{info['rtf']}")
        entrada = next((e for e in voces.CATALOGO.get(idioma, []) if e["id"] == nombre), None)
        if entrada:
            return (f"Calidad {entrada['calidad']} · {entrada['acento']} · "
                    f"{entrada['mb']} MB · {entrada['rtf']}")
        if nombre:
            mb = voces.tamano_mb_instalada(nombre, estado.LECTOR_DIR)
            return f"{nombre} · {mb:g} MB" if mb is not None else nombre
        return ""

    def _actualizar_voces(self, idioma, motor, guardada):
        disponibles = voces.instaladas(estado.LECTOR_DIR, motor, idioma)
        etiquetas = [voces.etiqueta_voz(v, motor, idioma) for v in disponibles]
        if etiquetas and etiquetas != self._voces_etiquetas:
            self.combo.configure(values=etiquetas)
        self._voces_lista = disponibles
        self._voces_etiquetas = etiquetas
        if guardada in disponibles:
            etiqueta = voces.etiqueta_voz(guardada, motor, idioma)
            if self.var_voz.get() != etiqueta:
                self.var_voz.set(etiqueta)
        elif disponibles:
            if self._sin_estrella(self.var_voz.get()) not in disponibles:
                self.var_voz.set(voces.etiqueta_voz(disponibles[0], motor, idioma))
        else:
            self.var_voz.set("")

    @staticmethod
    def _sin_estrella(nombre):
        return (nombre or "").replace("★", "").strip()

    def _texto_lector(self):
        if not estado.lector_en_marcha():
            return "parado"
        vivo = estado.lector_vivo() or {}
        if vivo.get("estado") == "cargando":
            return "cargando la voz…"
        if vivo.get("estado") == "leyendo":
            return f"leyendo con {vivo.get('voz') or '?'}"
        return "en marcha"

    def _actualizar_lector_linea(self):
        texto = self._texto_lector()
        self.l_lector.configure(text=texto, fg=ACENTO if texto != "parado" else GRIS)
        vivo = estado.lector_vivo() or {}
        motor = vivo.get("motor") or ""
        voz = vivo.get("voz") or ""
        detalle = " · ".join(p for p in (motor, voz) if p)
        if texto == "parado":
            linea = "Parado: el proceso está cerrado y no consume nada."
        elif vivo.get("estado") == "cargando":
            linea = f"Cargando la voz ({motor or 'motor'})… en cuanto esté, lista para leer."
        elif vivo.get("estado") == "leyendo":
            linea = f"Leyendo ahora con {voz or 'la voz elegida'}."
        else:
            linea = f"En marcha con {detalle or 'la voz elegida'}; esperando Ctrl+Alt+R."
        try:
            self.l_estado_lector.configure(text=linea)
        except tk.TclError:
            pass

    # --- GPU (en hilo: arranca procesos) ---

    def _refrescar_gpu(self):
        if self._gpu_hilo is not None and self._gpu_hilo.is_alive():
            return
        if time.monotonic() - self._gpu_ultimo < 3:
            return
        self._gpu_ultimo = time.monotonic()

        def trabajo():
            try:
                handy = control.handy_en_marcha()
                modelos = control.ollama_en_uso()
            except Exception:
                log.exception("No se pudo comprobar la GPU")
                handy, modelos = False, []
            try:
                self.raiz.after(0, self._poner_gpu, handy, modelos)
            except (tk.TclError, RuntimeError):
                pass

        self._gpu_hilo = threading.Thread(target=trabajo, daemon=True)
        self._gpu_hilo.start()

    def _poner_gpu(self, handy, modelos):
        self._handy_en_marcha = handy
        if handy:
            texto = "GPU en uso (Handy)"
        elif modelos:
            texto = f"GPU en uso (Ollama: {', '.join(modelos)})"
        else:
            texto = "GPU libre"
        self._gpu_texto = texto
        self.l_gpu.configure(text=texto, fg=ACENTO if (handy or modelos) else GRIS)
        self._actualizar_dictado()

    # --- Instalador de voces ---

    def abrir_instalador(self):
        if self._ventana_voces is not None and self._ventana_voces.winfo_exists():
            self._ventana_voces.lift()
            return
        ventana = tk.Toplevel(self.raiz)
        self._ventana_voces = ventana
        ventana.title("Instalar voces")
        ventana.configure(bg=FONDO)
        ventana.geometry(f"{round(470 * self.escala)}x{round(400 * self.escala)}")
        ventana.transient(self.raiz)
        idioma = self.cfg.get("idioma") or "es"
        tk.Label(ventana, text=f"Voces Piper · {IDIOMAS.get(idioma, idioma)}",
                 bg=FONDO, fg=TEXTO, font=(FAMILIA, 13, "bold")).pack(
                     anchor="w", padx=self._px(16), pady=(self._px(14), self._px(2)))
        tk.Label(ventana, text="Las voces se descargan del repositorio de Piper (60–120 MB).",
                 bg=FONDO, fg=GRIS, font=(FAMILIA, 9)).pack(anchor="w", padx=self._px(16))

        self._filas_voces = {}
        for entrada in voces.catalogo(idioma):
            fila = tk.Frame(ventana, bg=FONDO)
            fila.pack(fill="x", padx=self._px(16), pady=(self._px(8), 0))
            izq = tk.Frame(fila, bg=FONDO)
            izq.pack(side="left", fill="x", expand=True)
            tk.Label(izq, text=entrada["id"], bg=FONDO, fg=TEXTO,
                     font=(FAMILIA, 10, "bold")).pack(anchor="w")
            tk.Label(izq, text=entrada["descripcion"], bg=FONDO, fg=GRIS,
                     font=(FAMILIA, 8)).pack(anchor="w")
            der = tk.Frame(fila, bg=FONDO)
            der.pack(side="right")
            estado_voz = tk.Label(der, text="", bg=FONDO, fg=GRIS, font=(FAMILIA, 8))
            estado_voz.pack(side="left", padx=(0, self._px(6)))
            boton = tk.Button(der, text="Descargar", command=lambda e=entrada: self._descargar(e),
                              bg=TARJETA, fg=TEXTO, activebackground=ACENTO,
                              activeforeground=FONDO, relief="flat", bd=0,
                              highlightthickness=0, cursor="hand2",
                              padx=self._px(8), pady=self._px(2),
                              font=(FAMILIA, 9))
            boton.pack(side="left")
            self._filas_voces[entrada["id"]] = (estado_voz, boton)

        self._progreso_voces = tk.Label(ventana, text="", bg=FONDO, fg=GRIS,
                                        font=(FAMILIA, 9), wraplength=self._px(430),
                                        justify="left")
        self._progreso_voces.pack(side="bottom", anchor="w", padx=self._px(16),
                                  pady=(self._px(8), self._px(12)))
        self._refrescar_instalador(idioma)

    def _refrescar_instalador(self, idioma):
        for entrada in voces.catalogo(idioma):
            fila = self._filas_voces.get(entrada["id"])
            if not fila:
                continue
            etiqueta, boton = fila
            mb = voces.tamano_mb_instalada(entrada["id"], estado.LECTOR_DIR)
            if mb is not None:
                etiqueta.configure(text=f"instalada · {mb:g} MB")
                boton.configure(state="disabled", text="Instalada")
            else:
                etiqueta.configure(text=f"{entrada['mb']} MB")
                boton.configure(state="normal", text="Descargar")

    def _descargar(self, entrada):
        fila = self._filas_voces.get(entrada["id"])
        if fila:
            _etiqueta, boton = fila
            boton.configure(state="disabled", text="Descargando…")
        if self._progreso_voces is not None:
            self._progreso_voces.configure(text=f"Descargando {entrada['id']}…")

        def progreso(texto):
            try:
                self.raiz.after(0, self._progreso_voces.configure, {"text": texto})
            except (tk.TclError, RuntimeError):
                pass

        def trabajo():
            ok, mensaje = voces.descargar(entrada["id"], estado.LECTOR_DIR, progreso)
            try:
                self.raiz.after(0, self._fin_descarga, entrada["id"], ok, mensaje)
            except (tk.TclError, RuntimeError):
                pass

        threading.Thread(target=trabajo, daemon=True).start()

    def _fin_descarga(self, nombre, ok, mensaje):
        ventana = self._ventana_voces
        if ventana is None or not ventana.winfo_exists():
            return
        if self._progreso_voces is not None:
            self._progreso_voces.configure(text=mensaje, fg=GRIS if ok else ACENTO)
        self._refrescar_instalador(self.cfg.get("idioma") or "es")
        if ok:
            bloque = self._bloque_voz(crear=True)
            if (bloque.get("motor") or "piper") == "piper":
                bloque["voz"] = nombre
                estado.guardar_lector_json(self.cfg)
            else:
                mensaje = f"{nombre} instalada: cambia el motor a Piper para usarla"
        self._actualizar_todo()
        self._mensaje(mensaje, error=not ok)

    # --- Ventana: mostrar/ocultar/salir ---

    def mostrar(self):
        try:
            self.raiz.deiconify()
            self.raiz.lift()
            self.raiz.focus_force()
        except tk.TclError:
            pass

    def ocultar(self):
        try:
            ayuda.cerrar_todas()  # tooltips y ventanas de ayuda no deben quedar flotando
        except Exception:
            log.exception("No se pudieron cerrar las ayudas")
        try:
            self.raiz.withdraw()
        except tk.TclError:
            pass

    def alternar_visible(self):
        try:
            if self.raiz.state() == "withdrawn":
                self.mostrar()
            else:
                self.ocultar()
        except tk.TclError:
            pass

    def salir(self):
        """Termina el panel sin tocar el lector."""
        self.cerrando = True
        try:
            self._liberar_atajo_r()
        except Exception:
            log.exception("No se pudo soltar el atajo del aviso")
        try:
            ayuda.cerrar_todas()
            toast.cerrar_todos()
        except Exception:
            log.exception("No se pudieron cerrar las ventanas de ayuda")
        if self.icono is not None:
            try:
                self.icono.stop()
            except Exception:
                log.exception("No se pudo parar el icono de la bandeja")
        try:
            self.raiz.destroy()
        except tk.TclError:
            pass

    # --- Bandeja y atajo ---

    def _refrescar_icono(self):
        if self.icono is not None:
            try:
                self.icono.update_menu()
            except Exception:
                log.exception("No se pudo actualizar el menu del icono")

    def iniciar_bandeja(self):
        def abrir():
            self.raiz.after(0, self.mostrar)

        def lector(valor):
            self.raiz.after(0, self.poner_lector, valor)

        def salir():
            self.raiz.after(0, self.salir)

        try:
            self.icono = icono.crear_icono(abrir, lector, salir, lambda: self.estado)
        except Exception:
            log.exception("No se pudo crear el icono de la bandeja")
            self.icono = None
            return

        def run():
            try:
                self.icono.run()
            except Exception:
                log.exception("El icono de la bandeja ha dejado de funcionar")

        threading.Thread(target=run, daemon=True).start()

    def iniciar_atajo(self):
        atajo = self.cfg_panel.get("atajo") or "ctrl+alt+p"
        threading.Thread(target=self._escuchar_atajo, args=(atajo,), daemon=True).start()

    def _escuchar_atajo(self, atajo):
        try:
            if ES_WINDOWS:
                self._atajo_windows(atajo)
            else:
                self._atajo_linux(atajo)
        except Exception:
            log.exception("El atajo %s ha dejado de funcionar (la bandeja sigue)", atajo)

    def _atajo_windows(self, atajo):
        import ctypes
        from ctypes import wintypes

        datos = _parsear_atajo(atajo)
        if datos is None:
            log.warning("Atajo no valido: %s (se usa solo la bandeja)", atajo)
            return
        mod, vk = datos
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, 2, mod, vk):
            log.warning("El atajo %s ya esta en uso (se usa solo la bandeja)", atajo)
            return
        log.info("Atajo %s activo", atajo)
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    try:
                        self.raiz.after(0, self.alternar_visible)
                    except (tk.TclError, RuntimeError):
                        break
        finally:
            user32.UnregisterHotKey(None, 2)

    def _atajo_linux(self, atajo):
        from pynput import keyboard

        nombres = {"ctrl": "<ctrl>", "control": "<ctrl>", "alt": "<alt>", "shift": "<shift>",
                   "win": "<cmd>", "super": "<cmd>", "space": "<space>", "espacio": "<space>"}
        partes = []
        for parte in atajo.lower().split("+"):
            if parte in nombres:
                partes.append(nombres[parte])
            elif re.fullmatch(r"f([1-9]|1[0-2])", parte):
                partes.append(f"<{parte}>")
            else:
                partes.append(parte)
        combo = "+".join(partes)
        log.info("Atajo %s activo", combo)

        def al_pulsar():
            try:
                self.raiz.after(0, self.alternar_visible)
            except (tk.TclError, RuntimeError):
                pass

        with keyboard.GlobalHotKeys({combo: al_pulsar}) as h:
            h.join()

    # --- Arranque ---

    def arrancar(self):
        self._tick()
        self.iniciar_bandeja()
        self.iniciar_atajo()
        self.raiz.after(300, self._aplicar_estado_inicial)

    def _aplicar_estado_inicial(self):
        """Solo hay un estado: el lector encendido o apagado (los atajos conviven)."""
        encendido = bool(self.estado.get("lector"))
        log.info("Estado inicial: lector %s", "encendido" if encendido else "apagado")
        if not encendido:
            self._registrar_atajo_r()  # para avisar si se pulsa Ctrl+Alt+R
            return
        self._accion("Arrancando el lector…", control.arrancar_lector)

    def _tick(self):
        if self.cerrando:
            return
        try:
            self._actualizar_lector_linea()
            self._refrescar_gpu()
            self._vigilar_lector()
        except Exception:
            log.exception("Error refrescando el estado")
        try:
            self.raiz.after(1000, self._tick)
        except (tk.TclError, RuntimeError):
            pass

    def _vigilar_lector(self):
        """Si debe estar encendido y lleva ~10 s sin latido, se vuelve a arrancar."""
        if not self.estado.get("lector") or self.ocupado:
            self._sin_latido = 0
            return
        if estado.lector_en_marcha():
            self._sin_latido = 0
            return
        self._sin_latido = getattr(self, "_sin_latido", 0) + 1
        if self._sin_latido >= 10:
            self._sin_latido = 0
            log.info("El lector no responde: se vuelve a arrancar")
            self._liberar_atajo_r()  # por si el panel lo estaba escuchando
            self._accion("Reiniciando el lector…", control.arrancar_lector)


def una_sola_instancia():
    """Mutex de Windows / flock de Linux. None si ya hay un panel abierto."""
    try:
        estado.BASE.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    if ES_WINDOWS:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        handle = kernel32.CreateMutexW(None, False, "Local\\asistente-voz-local-panel")
        if not handle or kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return None
        return handle
    import fcntl
    f = open(estado.BASE / "panel.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def main():
    ap = argparse.ArgumentParser(description="Panel de voz del asistente local")
    ap.add_argument("--simular", action="store_true",
                    help="no toca Handy, Ollama ni el lector (pruebas de UI)")
    args = ap.parse_args()

    destinos = []
    try:
        destinos.append(logging.FileHandler(DIR / "panel.log", encoding="utf-8"))
    except OSError:
        pass
    if sys.stdout:
        destinos.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=destinos or [logging.NullHandler()],
                        format="%(asctime)s %(levelname)s %(message)s")

    if args.simular:
        control.SIMULAR = True
        log.info("Modo simulacion: Handy, Ollama y lector no se tocan")
    global _CANDADO
    _CANDADO = una_sola_instancia()
    if _CANDADO is None:
        log.info("Ya hay un panel abierto: se sale")
        return

    if ES_WINDOWS:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except OSError:
            pass

    raiz = tk.Tk()
    panel = Panel(raiz)
    panel.arrancar()
    try:
        raiz.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if panel.icono is not None:
            try:
                panel.icono.stop()
            except Exception:
                pass
        log.info("Panel cerrado")


if __name__ == "__main__":
    main()
