"""Lector de voz local (Piper/Kokoro) - Asistente de voz local.

Se queda en segundo plano con el modelo cargado. Al pulsar el atajo
(por defecto Ctrl+Alt+R) lee en voz alta el texto del
portapapeles; si ya esta leyendo, el mismo atajo lo para.

Uso:
  lector.py                    modo residente (lo arranca el inicio de sesion)
  lector.py --probar "texto"   lee ese texto (o el portapapeles si va vacio) y termina

Config: lector.json junto a este archivo (o config/lector.json del repo).
Motores: lector/motor.py (Piper por defecto; Kokoro como alternativa).
"""

import argparse
import json
import logging
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
ES_WINDOWS = sys.platform == "win32"

# pythonw.exe arranca sin stdout/stderr (None): se les da un destino valido antes de
# importar nada mas, por si alguna libreria escribe en ellos.
if sys.stdout is None or sys.stderr is None:
    import os
    _nulo = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = sys.stdout or _nulo
    sys.stderr = sys.stderr or _nulo

# Arrancado con el pythonw.exe base (sin consola, ver install.ps1): usar las librerias del .venv
_VENV_LIBS = DIR / ".venv" / "Lib" / "site-packages"
if ES_WINDOWS and sys.prefix == sys.base_prefix and _VENV_LIBS.is_dir():
    import site
    site.addsitedir(str(_VENV_LIBS))

import numpy as np
import onnxruntime
import sounddevice as sd

from leer_md import es_markdown, limpiar_texto, md_a_voz
import pronunciar
from motor import cargar_motor
from pildora import Pildora
from seleccion import texto_seleccionado

onnxruntime.set_default_logger_severity(3)  # el modelo fp16 llena el log de avisos inocuos


CONFIG_DEFECTO = {
    "atajo": "ctrl+alt+r",
    "idioma": "es",
    "voces": {
        "es": {"motor": "piper", "voz": "es_ES-davefx-medium"},
        "en": {"motor": "piper", "voz": "en_US-lessac-high"},
    },
    "velocidad": 1.0,
    "pausa_ms": 250,
    "leer_seleccion": True,
    "max_caracteres": 20000,
    "kokoro": {"modelo": "kokoro-v1.0.fp16.onnx", "voces": "voices-v1.0.bin"},
    "ingles_xtts": True,
}

log = logging.getLogger("lector")


# --- Configuracion ---

def _rutas_config():
    return (DIR / "lector.json", DIR.parent / "config" / "lector.json")


def ruta_config():
    """Primer lector.json que existe (el del repo solo si no hay uno instalado)."""
    for ruta in _rutas_config():
        if ruta.exists():
            return ruta
    return _rutas_config()[0]


def _mtime(ruta):
    try:
        return ruta.stat().st_mtime
    except OSError:
        return None


def _migrar(leido):
    """Esquema viejo (voz/modelo/voces sueltos, Kokoro) -> voces por idioma."""
    cfg = dict(leido)
    if not isinstance(cfg.get("voces"), dict):
        voz = cfg.pop("voz", None) or "em_alex"
        modelo = cfg.pop("modelo", None) or CONFIG_DEFECTO["kokoro"]["modelo"]
        bin_voces = cfg.pop("voces", None) or CONFIG_DEFECTO["kokoro"]["voces"]
        idioma = cfg.get("idioma") or "es"
        cfg["voces"] = {
            "es": {"motor": "kokoro", "voz": "em_alex"},
            "en": {"motor": "kokoro", "voz": "af_heart"},
        }
        cfg["voces"][idioma] = {"motor": "kokoro", "voz": voz}
        cfg["kokoro"] = {"modelo": modelo, "voces": bin_voces}
    else:
        cfg.pop("voz", None)   # restos del esquema viejo
        cfg.pop("modelo", None)
        voces = cfg.get("voces")
        cfg["voces"] = {**CONFIG_DEFECTO["voces"], **(voces if isinstance(voces, dict) else {})}
        kokoro = cfg.get("kokoro")
        cfg["kokoro"] = {**CONFIG_DEFECTO["kokoro"],
                         **(kokoro if isinstance(kokoro, dict) else {})}
    return {**CONFIG_DEFECTO, **cfg}


def cargar_config():
    ruta = ruta_config()
    try:
        with open(ruta, encoding="utf-8") as f:
            leido = json.load(f)
        if not isinstance(leido, dict):
            raise ValueError("el contenido no es un objeto JSON")
    except FileNotFoundError:
        return dict(CONFIG_DEFECTO)
    except (OSError, ValueError) as e:
        log.warning("No se pudo leer %s: %s (se usa la configuracion por defecto)", ruta, e)
        return dict(CONFIG_DEFECTO)
    return _migrar(leido)


# --- Estado compartido con el panel (spec 07) ---

ESTADO = DIR.parent / "estado.json"
VIVO = DIR.parent / "lector-vivo.json"
_ultimo_aviso_estado = [0.0, ""]


def _escribir_atomico(ruta, datos):
    """Escribe un JSON sin que el panel lo pueda leer a medias."""
    tmp = ruta.with_name(ruta.name + ".tmp")
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        os.replace(tmp, ruta)
    except OSError:
        pass  # el heartbeat no debe ensuciar el log ni tumbar el lector


def leer_estado():
    """estado.json del panel, o None si no existe / esta corrupto."""
    try:
        with open(ESTADO, encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        ahora = time.monotonic()
        if _ultimo_aviso_estado[1] != str(e) or ahora - _ultimo_aviso_estado[0] > 60:
            _ultimo_aviso_estado[:] = [ahora, str(e)]
            log.warning("estado.json ilegible (%s): se sigue funcionando", e)
        return None
    return datos if isinstance(datos, dict) else None



# --- Portapapeles ---

def leer_portapapeles():
    if ES_WINDOWS:
        return _portapapeles_windows()
    # Linux: Wayland (wl-paste) o X11 (xclip / xsel)
    for cmd in (["wl-paste", "--no-newline"],
                ["xclip", "-o", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--output"]):
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=3)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="replace")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    log.warning("No hay xclip, xsel ni wl-paste para leer el portapapeles")
    return ""


def _portapapeles_windows():
    import ctypes
    import time

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.GetClipboardData.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    CF_UNICODETEXT = 13

    # Otra app puede tener el portapapeles abierto un momento: se reintenta hasta 2 s
    for _ in range(40):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        log.warning("Portapapeles ocupado por otra aplicacion")
        return ""
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            formatos, f = [], 0
            while True:
                f = user32.EnumClipboardFormats(f)
                if not f:
                    break
                formatos.append(f)
            log.info("El portapapeles no tiene texto (formatos: %s)", formatos)
            return ""
        p = kernel32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p) if p else ""
        finally:
            kernel32.GlobalUnlock(h)
    finally:
        user32.CloseClipboard()


def escribir_portapapeles(texto):
    """Deja ``texto`` en el portapapeles (para restaurar lo que había)."""
    if ES_WINDOWS:
        return _escribir_portapapeles_windows(texto)
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            r = subprocess.run(cmd, input=texto.encode("utf-8"), capture_output=True, timeout=3)
            if r.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def _escribir_portapapeles_windows(texto):
    import ctypes
    import time

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x0002

    for _ in range(20):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        return False
    try:
        datos = (texto or "") + "\0"
        tam = len(datos) * ctypes.sizeof(ctypes.c_wchar)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, tam)
        if not handle:
            return False
        puntero = kernel32.GlobalLock(handle)
        if not puntero:
            return False
        try:
            ctypes.memmove(puntero, ctypes.create_unicode_buffer(datos), tam)
        finally:
            kernel32.GlobalUnlock(handle)
        user32.EmptyClipboard()
        return bool(user32.SetClipboardData(CF_UNICODETEXT, handle))
    finally:
        user32.CloseClipboard()


# --- Texto ---

def limpiar(texto):
    """Saneado del texto normal (no Markdown): mismas reglas que el Markdown."""
    return limpiar_texto(texto)


def trocear(texto, maximo=200, juntar=120):
    """Divide en frases para empezar a hablar enseguida.

    Cada linea (fila de tabla, elemento de lista) y cada frase es un trozo; los
    de mas de ``maximo`` se cortan por ; y luego por comas. Los trozos muy
    cortos («Lista.», «Fechas:») se juntan con el siguiente, sin pasar de
    ``juntar`` caracteres: XTTS se atasca con trozos largos.
    """
    trozos = []
    for parte in re.split(r"(?<=[.!?…])\s+|\n+", texto):
        parte = re.sub(r"\s+", " ", parte).strip()
        if not parte:
            continue
        while len(parte) > maximo:
            corte = parte.rfind("; ", 0, maximo)
            if corte <= 0:
                corte = parte.rfind(", ", 0, maximo)
            corte = corte + 1 if corte > 0 else maximo
            trozos.append(parte[:corte].strip())
            parte = parte[corte:].strip()
        if parte:
            trozos.append(parte)
    unidos = []
    pendiente = ""
    for t in trozos:
        if pendiente:
            if len(pendiente) + len(t) < juntar:
                t = pendiente + " " + t
            else:
                unidos.append(pendiente)
            pendiente = ""
        if len(t) < 20:
            pendiente = t
        else:
            unidos.append(t)
    if pendiente:
        if unidos and len(unidos[-1]) + len(pendiente) < juntar:
            unidos[-1] += " " + pendiente
        else:
            unidos.append(pendiente)
    return unidos


# --- Lectura ---

class Lector:
    def __init__(self, cfg):
        self.cfg = cfg
        self._ruta_config = ruta_config()
        self._mtime_config = _mtime(self._ruta_config)
        self.cerrando = False
        self.hilo = None
        self.parar = threading.Event()
        # Lo lee la pildora: "inactivo" | "preparando" | "leyendo" | "aviso",
        # y 9 niveles 0..1
        self.estado = "inactivo"
        self.niveles = [0.0] * 9
        self.salida = None
        self.progreso = time.monotonic()
        self.motor = None
        self.motor_nombre = None
        self._cargando = False
        self.cargando_desde = None
        self.cargando_visible = False
        self.aviso_texto = ""
        self.aviso_hasta = 0.0
        self.error_texto = ""
        self.error_hasta = 0.0
        self._leer_cuando_listo = False

    # --- Motor y configuracion ---

    def cargar_en_segundo_plano(self):
        """Carga la voz sin bloquear: la pildora puede avisar mientras tanto."""
        threading.Thread(target=self._cargar_motor, daemon=True).start()

    def _cargar_motor(self):
        """Carga el motor de la config actual. Un fallo no tumba el proceso."""
        self._cargando = True
        self.estado = "cargando"
        self.cargando_desde = time.monotonic()
        log.info("Cargando la voz (%s)...", self.cfg.get("voces", {}).get(
            self.cfg.get("idioma") or "es", {}).get("motor", "?"))
        try:
            self.motor = cargar_motor(self.cfg, DIR)
            self.motor_nombre = self.motor.nombre
            self.motor.crear("Hola.")  # calienta el modelo: la primera frase suena ya
            log.info("Listo (voz %s, %d Hz)", self.motor_nombre, self.motor.sr)
        except Exception as e:
            log.error("No se pudo cargar la voz: %s", e)
            self.motor = None
            self.motor_nombre = None
            self.error_texto = "No se pudo cargar la voz"
            self.error_hasta = time.monotonic() + 5  # se ve en la píldora al pulsar
            avisar()
        finally:
            self._cargando = False
            self.cargando_desde = None
            self.cargando_visible = False
            self.estado = "inactivo"
            pendiente = self._leer_cuando_listo
            self._leer_cuando_listo = False
        if pendiente and self.motor is not None:
            self.alternar()

    def _config_cambiada(self):
        ruta = ruta_config()
        return ruta != self._ruta_config or _mtime(ruta) != self._mtime_config

    def _recargar_config(self):
        """Relee lector.json y reinicia el motor con la voz nueva."""
        ruta = ruta_config()
        mtime = _mtime(ruta)  # antes de leer: si cambia mientras, se vera en la proxima
        self.cfg = cargar_config()
        self._ruta_config = ruta
        self._mtime_config = mtime
        log.info("Configuración recargada")
        self.cargando_visible = True  # el usuario ve que esta cargando la voz nueva
        self._cargar_motor()

    def _recargar_en_segundo_plano(self):
        threading.Thread(target=self._recargar_config, daemon=True).start()

    def comprobar_estado(self):
        """Lee estado.json (lo escribe el panel). True si hay que cerrar la app.

        Solo hay encendido/apagado: los atajos de dictado y lectura conviven, no
        hay modos que se excluyan.
        """
        datos = leer_estado()
        if datos is None:  # sin estado.json: encendido (como siempre)
            return False
        if datos.get("lector") is False:
            if not self.cerrando:
                log.info("El panel ha apagado el lector: se cierra la aplicacion")
            self.cerrando = True
            self.parar.set()
            return True
        return False

    def latir(self):
        """lector-vivo.json cada 2 s, para que el panel sepa que seguimos vivos."""
        while not self.cerrando:
            motor = self.motor
            _escribir_atomico(VIVO, {
                "vivo": time.time(),
                "estado": self.estado,
                "motor": getattr(motor, "motor", "") if motor else "",
                "voz": getattr(motor, "voz", "") if motor else "",
            })
            time.sleep(2)

    # --- Atajo ---

    def alternar(self, texto=None, forzar=False):
        """Atajo pulsado: si esta leyendo, para; si no, lee el portapapeles.

        ``forzar`` lo usa el modo de prueba (--probar): ignora si el panel tiene
        el lector apagado.
        """
        if self.cerrando:
            return
        if self.hilo and self.hilo.is_alive():
            log.info("Parado por el usuario")
            self.parar.set()
            return
        if self.motor is None and self._cargando:
            # Se ha pulsado mientras carga la voz: se avisa en la pildora y se lee al terminar
            self.cargando_visible = True
            self._leer_cuando_listo = True
            log.info("La voz se está cargando: se leerá en cuanto esté")
            return
        if not forzar:
            if self.comprobar_estado():
                return
        if self._config_cambiada():
            # Recargar la voz tarda (XTTS ~15 s): se hace en segundo plano y se lee
            # al terminar, para no dejar el atajo sin responder.
            if self._cargando:
                self.cargando_visible = True
                self._leer_cuando_listo = True
                return
            self.cargando_visible = True
            self._leer_cuando_listo = True
            log.info("Configuración nueva: recargando la voz; se leerá al terminar")
            self._recargar_en_segundo_plano()
            return
        if self.motor is None:
            avisar()
            self._aviso_visible("La voz no está cargada")
            return
        if texto is None:
            portapapeles = leer_portapapeles()
            texto = ""
            if self.cfg.get("leer_seleccion", True):
                # Primero lo seleccionado en la ventana con el foco; si no hay, el portapapeles
                texto = texto_seleccionado(portapapeles)
                if texto:
                    log.info("Leyendo la selección (%d caracteres)", len(texto))
            if not texto:
                texto = portapapeles
        texto = texto or ""
        if es_markdown(texto):
            log.info("Texto en Markdown: se omite el codigo")
            texto = md_a_voz(texto)
        else:
            texto = limpiar(texto)
        texto = texto[: self.cfg["max_caracteres"]].strip()
        if not texto:
            log.info("Nada que leer en el portapapeles")
            avisar()
            self._aviso_visible("Nada que leer")
            return
        self.parar = threading.Event()
        self.hilo = threading.Thread(target=self._leer, args=(texto, self.parar), daemon=True)
        self.hilo.start()

    def _aviso_visible(self, texto="Nada que leer"):
        """Pildora gris 2 s con un mensaje: no habia texto, fallo de voz, etc."""
        self.aviso_texto = texto
        self.aviso_hasta = time.monotonic() + 2.0
        self.estado = "aviso"

        def quitar():
            if self.estado == "aviso":
                self.estado = "inactivo"

        threading.Timer(2.0, quitar).start()

    def _leer(self, texto, parar):
        motor = self.motor
        sr = motor.sr
        tam = max(1, int(round(sr * 0.05)))  # bloques de 50 ms
        comprobar_cada = max(1, int(round(0.5 / 0.05)))  # config cada ~0,5 s
        cola = queue.Queue(maxsize=3)
        self.progreso = time.monotonic()
        idioma = self.cfg.get("idioma") or "es"
        # Tramos en ingles con la misma voz: solo XTTS sabe cambiar de idioma (spec 17)
        ingles = getattr(motor, "motor", "") == "xtts" and self.cfg.get("ingles_xtts", True)

        def producir():
            try:
                for frase in trocear(texto):
                    if parar.is_set():
                        break
                    audio = pronunciar.generar(motor, frase, idioma, ingles)
                    if audio is None:
                        continue
                    while not parar.is_set():
                        try:
                            cola.put(audio, timeout=0.2)
                            break
                        except queue.Full:
                            continue
            except Exception:
                log.exception("Error generando la voz")
            finally:
                try:
                    cola.put_nowait(None)  # si la cola esta llena, el hilo de audio ya no la lee
                except queue.Full:
                    pass

        threading.Thread(target=producir, daemon=True).start()
        log.info("Leyendo %d caracteres con %s", len(texto), self.motor_nombre)
        self.estado = "preparando"
        espera = 240 if getattr(motor, "carga_lenta", False) else 25
        # Los motores lentos (XTTS/Chatterbox) generan una frase entera de golpe: dar margen
        atascado = 150 if getattr(motor, "carga_lenta", False) else 10
        threading.Thread(target=self._vigilar, args=(parar,),
                         kwargs={"espera": espera, "atascado": atascado}, daemon=True).start()

        def config_nueva():
            log.info("Configuración nueva: se aplicará en la próxima lectura")
            parar.set()

        bloques = 0
        try:
            with sd.OutputStream(samplerate=sr, channels=1, dtype="float32") as salida:
                self.salida = salida
                while not parar.is_set():
                    try:
                        item = cola.get(timeout=0.2)
                    except queue.Empty:
                        if self._config_cambiada():
                            config_nueva()
                        continue
                    if item is None:
                        break
                    audio = np.nan_to_num(np.asarray(item, dtype=np.float32),
                                          nan=0.0, posinf=1.0, neginf=-1.0)
                    self.estado = "leyendo"
                    # Bloques de 50 ms: parar es inmediato y las barras siguen la voz
                    for i in range(0, len(audio), tam):
                        if parar.is_set():
                            break
                        bloque = audio[i:i + tam]
                        self.niveles = niveles_voz(bloque, sr=sr)
                        salida.write(bloque)
                        self.progreso = time.monotonic()
                        bloques += 1
                        if bloques >= comprobar_cada:
                            bloques = 0
                            if self._config_cambiada():
                                config_nueva()
                                break
                if parar.is_set():
                    salida.abort()
        except Exception:
            log.exception("Error reproduciendo el audio")
        finally:
            parar.set()  # el vigilante de esta lectura ya no hace falta
            if self.parar is parar:  # sigue siendo esta lectura la actual
                self.salida = None
                self.estado = "inactivo"
                self.niveles = [0.0] * 9
            if self._config_cambiada():
                self._recargar_config()  # la voz nueva entra en la proxima lectura

    def _vigilar(self, parar, espera=25, atascado=10):
        """Red de seguridad: PortAudio puede dejar el write bloqueado para siempre
        (dispositivo que desaparece). Entonces la pildora se quedaba en pantalla."""
        while not parar.is_set():
            time.sleep(0.5)
            if self.parar is not parar or not (self.hilo and self.hilo.is_alive()):
                return  # la lectura ya termino: no hay nada que vigilar
            limite = atascado if self.estado == "leyendo" else espera
            if time.monotonic() - self.progreso <= limite:
                continue
            log.warning("La reproduccion se ha atascado: se corta (%s)", self.estado)
            parar.set()
            salida = self.salida
            if salida is not None:
                try:
                    salida.abort()
                except Exception:
                    log.exception("No se pudo abortar el audio")
            if self.parar is parar:
                self.estado = "inactivo"
                self.niveles = [0.0] * 9
                self.hilo = None  # el atajo vuelve a responder
            return



# Bandas de frecuencia (Hz) de las 9 barras, de graves a agudos
_BANDAS = np.geomspace(90, 5000, 10)


def niveles_voz(bloque, sr=24000):
    """9 niveles 0..1 de un bloque de audio, para las barras de la pildora."""
    if len(bloque) < 64:
        return [0.0] * 9
    muestra = np.nan_to_num(bloque, nan=0.0, posinf=1.0, neginf=-1.0)
    espectro = np.abs(np.fft.rfft(muestra * np.hanning(len(muestra))))
    frec = np.fft.rfftfreq(len(muestra), 1 / sr)
    energia = np.array([espectro[(frec >= a) & (frec < b)].mean() for a, b in zip(_BANDAS, _BANDAS[1:])])
    volumen = min(1.0, float(np.sqrt(np.mean(muestra ** 2))) * 14)
    valores = np.sqrt(energia / (energia.max() + 1e-9)) * volumen  # raiz: agudos visibles
    # PIL revienta con NaN (y dejaba la pildora congelada en pantalla)
    return [float(min(1.0, max(0.0, v))) if np.isfinite(v) else 0.0 for v in valores]



def avisar():
    if ES_WINDOWS:
        import winsound
        winsound.MessageBeep()


# --- Atajo global ---

def escuchar_windows(atajo, al_pulsar):
    import ctypes
    from ctypes import wintypes

    mods = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}
    teclas = {"space": 0x20, "espacio": 0x20, "enter": 0x0D, "tab": 0x09}
    mod, vk = 0x4000, None  # 0x4000 = MOD_NOREPEAT
    for parte in atajo.lower().split("+"):
        if parte in mods:
            mod |= mods[parte]
        elif parte in teclas:
            vk = teclas[parte]
        elif re.fullmatch(r"f([1-9]|1[0-2])", parte):
            vk = 0x6F + int(parte[1:])
        elif len(parte) == 1 and parte.isalnum():
            vk = ord(parte.upper())
    if vk is None:
        raise SystemExit(f"Atajo no valido: {atajo}")

    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, 1, mod, vk):
        log.error("El atajo %s ya esta en uso (otra app u otro lector abierto)", atajo)
        avisar()
        raise SystemExit(1)
    log.info("Atajo %s activo", atajo)
    msg = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:  # WM_HOTKEY
                al_pulsar()
    finally:
        user32.UnregisterHotKey(None, 1)


def escuchar_linux(atajo, al_pulsar):
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
    with keyboard.GlobalHotKeys({combo: al_pulsar}) as h:
        h.join()


def una_sola_instancia():
    """En Linux, evita dos lectores a la vez (en Windows lo impide RegisterHotKey)."""
    if ES_WINDOWS:
        return None
    import fcntl
    f = open(DIR / "lector.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("Ya hay un lector en marcha")
    return f


def main():
    ap = argparse.ArgumentParser(description="Lector de voz local (Piper/Kokoro)")
    ap.add_argument("--probar", nargs="?", const="", metavar="TEXTO",
                    help="lee el texto (o el portapapeles) y termina")
    args = ap.parse_args()

    destinos = [logging.FileHandler(DIR / "lector.log", encoding="utf-8")]
    if sys.stdout:  # pythonw no tiene consola
        destinos.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=destinos,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("phonemizer").setLevel(logging.ERROR)  # avisos inocuos de espeak

    cfg = cargar_config()
    if args.probar is not None:
        # Modo de prueba: sin pildora, sin tocar estado.json ni el heartbeat
        lector = Lector(cfg)
        lector._cargar_motor()
        lector.alternar(args.probar or None, forzar=True)
        if lector.hilo:
            lector.hilo.join()
        return

    candado = una_sola_instancia()  # noqa: F841 (se mantiene abierto mientras vive el proceso)
    lector = Lector(cfg)
    if lector.comprobar_estado():  # el panel lo tiene apagado: no se abre la pildora
        return
    pildora = Pildora(lector)  # Tk vive en el hilo principal; el atajo, en otro
    threading.Thread(target=lector.latir, daemon=True).start()
    lector.cargar_en_segundo_plano()  # la voz se carga sin bloquear la pildora ni el atajo

    def vigilar_estado():
        """Sondeo de estado.json cada ~0,5 s desde el hilo de Tk (sin hilos nuevos)."""
        try:
            if lector.comprobar_estado():
                pildora.cerrar()
                return
        except Exception:
            log.exception("Error comprobando el estado del panel")
        pildora.raiz.after(500, vigilar_estado)

    pildora.raiz.after(500, vigilar_estado)

    def escuchar():
        try:
            if ES_WINDOWS:
                escuchar_windows(cfg["atajo"], lector.alternar)
            else:
                escuchar_linux(cfg["atajo"], lector.alternar)
        except BaseException:
            log.exception("El atajo ha dejado de funcionar")
        pildora.cerrar()  # sin atajo no tiene sentido seguir

    threading.Thread(target=escuchar, daemon=True).start()
    try:
        pildora.ejecutar()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
