"""Lector de voz local (Kokoro-82M) - Asistente de voz local.

Se queda en segundo plano con el modelo cargado. Al pulsar el atajo
(por defecto Ctrl+Alt+R) lee en voz alta el texto del
portapapeles; si ya esta leyendo, el mismo atajo lo para.

Uso:
  lector.py                    modo residente (lo arranca el inicio de sesion)
  lector.py --probar "texto"   lee ese texto (o el portapapeles si va vacio) y termina

Config: lector.json junto a este archivo (o config/lector.json del repo).
Modelo: carpeta modelo/ junto a este archivo.
"""

import argparse
import json
import logging
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
import onnxruntime
import sounddevice as sd
from kokoro_onnx import Kokoro

from leer_md import es_markdown, md_a_voz
from pildora import Pildora

onnxruntime.set_default_logger_severity(3)  # el modelo fp16 llena el log de avisos inocuos

DIR = Path(__file__).resolve().parent
ES_WINDOWS = sys.platform == "win32"

CONFIG_DEFECTO = {
    "atajo": "ctrl+alt+r",
    "voz": "em_alex",
    "velocidad": 1.0,
    "idioma": "es",
    "modelo": "kokoro-v1.0.fp16.onnx",
    "voces": "voices-v1.0.bin",
    "max_caracteres": 20000,
}

log = logging.getLogger("lector")


# --- Configuracion ---

def cargar_config():
    for ruta in (DIR / "lector.json", DIR.parent / "config" / "lector.json"):
        if ruta.exists():
            with open(ruta, encoding="utf-8") as f:
                return {**CONFIG_DEFECTO, **json.load(f)}
    return dict(CONFIG_DEFECTO)


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


# --- Texto ---

def limpiar(texto):
    texto = re.sub(r"https?://\S+", "enlace", texto)
    texto = re.sub(r"[*_#`>|~]+", " ", texto)  # restos de markdown
    return texto


def trocear(texto, maximo=300):
    """Divide en frases para empezar a hablar enseguida."""
    trozos = []
    for parte in re.split(r"(?<=[.!?…:;])\s+|\n+", texto):
        parte = re.sub(r"\s+", " ", parte).strip()
        if not parte:
            continue
        # Frases muy largas: se cortan por comas
        while len(parte) > maximo:
            corte = parte.rfind(", ", 0, maximo)
            corte = corte + 1 if corte > 0 else maximo
            trozos.append(parte[:corte].strip())
            parte = parte[corte:].strip()
        if parte:
            trozos.append(parte)
    # Se juntan los trozos sueltos muy cortos ("1.", "Hola.") con el siguiente
    unidos = []
    for t in trozos:
        if unidos and (len(unidos[-1]) < 20 or len(t) < 20):
            unidos[-1] += " " + t
        else:
            unidos.append(t)
    return unidos


# --- Lectura ---

class Lector:
    def __init__(self, cfg):
        self.cfg = cfg
        modelo_dir = DIR / "modelo"
        log.info("Cargando modelo %s", cfg["modelo"])
        self.kokoro = Kokoro(str(modelo_dir / cfg["modelo"]), str(modelo_dir / cfg["voces"]))
        self.kokoro.create("Hola.", voice=cfg["voz"], speed=cfg["velocidad"], lang=cfg["idioma"])
        self.hilo = None
        self.parar = threading.Event()
        # Lo lee la pildora: "inactivo" | "preparando" | "leyendo", y 9 niveles 0..1
        self.estado = "inactivo"
        self.niveles = [0.0] * 9
        log.info("Listo (voz %s)", cfg["voz"])

    def alternar(self, texto=None):
        """Atajo pulsado: si esta leyendo, para; si no, lee el portapapeles."""
        if self.hilo and self.hilo.is_alive():
            log.info("Parado por el usuario")
            self.parar.set()
            return
        if texto is None:
            texto = leer_portapapeles()
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
            self._aviso_visible()
            return
        self.parar = threading.Event()
        self.hilo = threading.Thread(target=self._leer, args=(texto, self.parar), daemon=True)
        self.hilo.start()

    def _aviso_visible(self):
        """Pildora gris 1,2 s: se pulso el atajo pero no hay texto."""
        self.estado = "aviso"

        def quitar():
            if self.estado == "aviso":
                self.estado = "inactivo"

        threading.Timer(1.2, quitar).start()

    def _leer(self, texto, parar):
        cfg = self.cfg
        cola = queue.Queue(maxsize=3)

        def producir():
            try:
                for frase in trocear(texto):
                    if parar.is_set():
                        break
                    audio, sr = self.kokoro.create(frase, voice=cfg["voz"], speed=cfg["velocidad"],
                                                   lang=cfg["idioma"])
                    while not parar.is_set():
                        try:
                            cola.put((audio, sr), timeout=0.2)
                            break
                        except queue.Full:
                            continue
            except Exception:
                log.exception("Error generando la voz")
            finally:
                cola.put(None)

        threading.Thread(target=producir, daemon=True).start()
        log.info("Leyendo %d caracteres", len(texto))
        self.estado = "preparando"
        try:
            with sd.OutputStream(samplerate=24000, channels=1, dtype="float32") as salida:
                while not parar.is_set():
                    item = cola.get()
                    if item is None:
                        break
                    audio = np.asarray(item[0], dtype=np.float32)
                    self.estado = "leyendo"
                    # Bloques de 50 ms: parar es inmediato y las barras siguen la voz
                    for i in range(0, len(audio), 1200):
                        if parar.is_set():
                            break
                        bloque = audio[i:i + 1200]
                        self.niveles = niveles_voz(bloque)
                        salida.write(bloque)
                if parar.is_set():
                    salida.abort()
        except Exception:
            log.exception("Error reproduciendo el audio")
        finally:
            self.estado = "inactivo"
            self.niveles = [0.0] * 9


# Bandas de frecuencia (Hz) de las 9 barras, de graves a agudos
_BANDAS = np.geomspace(90, 5000, 10)


def niveles_voz(bloque, sr=24000):
    """9 niveles 0..1 de un bloque de audio, para las barras de la pildora."""
    if len(bloque) < 64:
        return [0.0] * 9
    espectro = np.abs(np.fft.rfft(bloque * np.hanning(len(bloque))))
    frec = np.fft.rfftfreq(len(bloque), 1 / sr)
    energia = np.array([espectro[(frec >= a) & (frec < b)].mean() for a, b in zip(_BANDAS, _BANDAS[1:])])
    volumen = min(1.0, float(np.sqrt(np.mean(bloque ** 2))) * 14)
    return list(np.sqrt(energia / (energia.max() + 1e-9)) * volumen)  # raiz: agudos visibles


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
    ap = argparse.ArgumentParser(description="Lector de voz local (Kokoro)")
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
        lector = Lector(cfg)
        lector.alternar(args.probar or None)
        if lector.hilo:
            lector.hilo.join()
        return

    candado = una_sola_instancia()  # noqa: F841 (se mantiene abierto mientras vive el proceso)
    lector = Lector(cfg)
    pildora = Pildora(lector)  # Tk vive en el hilo principal; el atajo, en otro

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
