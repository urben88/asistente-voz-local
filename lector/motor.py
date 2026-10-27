"""Motores de voz del lector: Piper (por defecto) y Kokoro.

Los imports de piper/kokoro son perezosos (dentro de cada clase) para que el
lector pueda importarse sin el modelo instalado y para que un fallo de una voz
no tumbe el proceso.

Interfaz comun:
  - ``.sr``      frecuencia de muestreo del motor (int)
  - ``.nombre``  identificador legible, p. ej. ``piper:es_ES-davefx-medium``
  - ``.crear(frase) -> np.ndarray float32 mono``
"""

import logging
import os
from pathlib import Path

import numpy as np

log = logging.getLogger("lector.motor")


def _sanear(audio):
    """float32 mono y sin NaN/inf (PIL y sounddevice no los toleran)."""
    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
    return np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)


def _recortar(audio, sr, umbral=0.05, margen_ms=40, fundido_ms=25):
    """Quita el ruido y la respiración de los bordes y suaviza la entrada y la salida.

    Ventanas de 20 ms: se conserva desde la primera hasta la última cuyo RMS
    supera ``umbral`` del máximo, más ``margen_ms``; luego fundido corto.
    """
    if audio.size == 0:
        return audio
    paso = max(1, int(sr * 0.02))
    n = audio.size // paso
    if n < 3:
        return audio
    rms = np.sqrt(np.mean(audio[: n * paso].reshape(n, paso) ** 2, axis=1))
    fuertes = np.nonzero(rms > umbral * rms.max())[0]
    if fuertes.size == 0:
        return audio
    margen = int(sr * margen_ms / 1000)
    inicio = max(0, fuertes[0] * paso - margen // 2)
    fin = min(audio.size, (fuertes[-1] + 1) * paso + margen)
    audio = audio[inicio:fin].copy()
    entrada = min(audio.size, int(sr * 0.005))
    salida = min(audio.size, int(sr * fundido_ms / 1000))
    audio[:entrada] *= np.linspace(0.0, 1.0, entrada, dtype=np.float32)
    audio[audio.size - salida:] *= np.linspace(1.0, 0.0, salida, dtype=np.float32)
    return audio


def _silencio(ms, sr):
    muestras = max(0, int(round(sr * float(ms) / 1000.0)))
    return np.zeros(muestras, dtype=np.float32)


def _pausa_por_signo(frase, pausa_ms):
    """Pausa final segun el ultimo signo: frase, dos puntos o coma."""
    limpia = (frase or "").rstrip()
    signo = limpia[-1] if limpia else ""
    if signo == ",":
        factor = 0.35
    elif signo and signo in ":;":
        factor = 0.60
    else:
        factor = 1.0
    return max(0, int(round(float(pausa_ms) * factor)))


class PiperMotor:
    """Piper local (CPU). Voces en ``<dir_lector>/voces/piper/<voz>.onnx``."""

    motor = "piper"

    def __init__(self, ruta_onnx, velocidad=1.0, pausa_ms=250):
        from piper import PiperVoice

        self.ruta = Path(ruta_onnx)
        self.voz = self.ruta.stem
        self.nombre = f"piper:{self.voz}"
        self.velocidad = float(velocidad) if float(velocidad) > 0 else 1.0
        self.pausa_ms = max(0, int(pausa_ms))
        self._voz = PiperVoice.load(str(self.ruta))
        self.sr = int(self._voz.config.sample_rate)

    def crear(self, frase):
        from piper import SynthesisConfig

        config = SynthesisConfig(length_scale=1.0 / self.velocidad)
        trozos = [_sanear(c.audio_float_array) for c in self._voz.synthesize(frase, config)]
        audio = np.concatenate(trozos) if trozos else np.zeros(0, dtype=np.float32)
        return np.concatenate([audio, _silencio(_pausa_por_signo(frase, self.pausa_ms), self.sr)])


class KokoroMotor:
    """Kokoro-82M (alternativa). Modelo y voces en ``<dir_lector>/modelo/``."""

    motor = "kokoro"

    def __init__(self, dir_modelo, modelo, voces, voz, velocidad=1.0, idioma="es",
                 pausa_ms=250):
        from kokoro_onnx import Kokoro

        self.dir_modelo = Path(dir_modelo)
        self.voz = voz
        self.nombre = f"kokoro:{voz}"
        self.velocidad = float(velocidad) if float(velocidad) > 0 else 1.0
        self.idioma = idioma
        self.pausa_ms = max(0, int(pausa_ms))
        self.sr = 24000
        self._kokoro = Kokoro(str(self.dir_modelo / modelo), str(self.dir_modelo / voces))

    def crear(self, frase):
        audio, _sr = self._kokoro.create(frase, voice=self.voz, speed=self.velocidad,
                                         lang=self.idioma)
        # Misma respiracion que Piper: si no, las frases se pegan unas a otras
        pausa = _silencio(_pausa_por_signo(frase, self.pausa_ms), self.sr)
        return np.concatenate([_sanear(audio), pausa])


class ChatterboxMotor:
    """Chatterbox Multilingual (GPU): la voz más natural, más lenta que el tiempo real.

    Usa `chatterbox-tts` + torch; el modelo (~3 GB) se descarga la primera vez.
    """

    motor = "chatterbox"
    carga_lenta = True

    def __init__(self, idioma="es", pausa_ms=250):
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self.idioma = (idioma or "es").lower()
        self.pausa_ms = max(0, int(pausa_ms))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info("Cargando Chatterbox (%s) en %s", self.idioma, self.device)
        self._modelo = ChatterboxMultilingualTTS.from_pretrained(device=torch.device(self.device))
        self.sr = int(getattr(self._modelo, "sr", 24000))
        self.voz = "por defecto"
        self.nombre = f"chatterbox:{self.idioma}"

    def crear(self, frase):
        wav = self._modelo.generate(frase, language_id=self.idioma)
        audio = numpy_tensor(wav)
        return np.concatenate([audio, _silencio(_pausa_por_signo(frase, self.pausa_ms), self.sr)])


def numpy_tensor(wav):
    """Tensor de torch (o lista) -> float32 mono saneado."""
    if hasattr(wav, "detach"):
        wav = wav.detach().cpu().numpy()
    return _sanear(np.asarray(wav, dtype=np.float32).reshape(-1))


class XttsMotor:
    """XTTS-v2 (GPU): 58 voces, 17 idiomas, ~1,5 veces más rápido que el tiempo real."""

    motor = "xtts"
    carga_lenta = True

    def __init__(self, idioma="es", voz="Luis Moray", pausa_ms=250, velocidad=1.0):
        os.environ.setdefault("COQUI_TOS_AGREED", "1")  # licencia aceptada al instalar
        import torch
        from TTS.api import TTS

        self.idioma = (idioma or "es").lower()
        self.voz = voz or "Luis Moray"
        self.pausa_ms = max(0, int(pausa_ms))
        self.velocidad = float(velocidad) if float(velocidad) > 0 else 1.0
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sr = 24000
        self.nombre = f"xtts:{self.voz}"
        log.info("Cargando XTTS (%s, %s) en %s", self.voz, self.idioma, self.device)
        self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)

    def crear(self, frase):
        audio = self._generar(frase, self.idioma)
        return np.concatenate([audio, _silencio(_pausa_por_signo(frase, self.pausa_ms), self.sr)])

    def _generar(self, texto, idioma):
        try:
            wav = self._tts.tts(text=texto, speaker=self.voz, language=idioma,
                                speed=self.velocidad, split_sentences=False)
        except TypeError:  # versiones sin speed
            wav = self._tts.tts(text=texto, speaker=self.voz, language=idioma)
        return _recortar(_sanear(np.asarray(wav, dtype=np.float32).reshape(-1)), self.sr)

    def crear_segmentos(self, segmentos):
        """[(texto, idioma)] -> audio con la misma voz; pausa por signo solo al final (spec 17)."""
        trozos = []
        for i, (texto, idioma) in enumerate(segmentos):
            if i:
                trozos.append(_silencio(40, self.sr))
            trozos.append(self._generar(texto, idioma))
        final = segmentos[-1][0]
        trozos.append(_silencio(_pausa_por_signo(final, self.pausa_ms), self.sr))
        return np.concatenate(trozos)


def _error(ruta, que):
    return FileNotFoundError(
        f"Falta {que}: no existe «{ruta}». Instala la voz desde el panel de voz.")


def cargar_motor(cfg, dir_lector):
    """Crea el motor que pide la config (esquema nuevo de la spec 07)."""
    dir_lector = Path(dir_lector)
    idioma = cfg.get("idioma") or "es"
    voces = cfg.get("voces")
    if not isinstance(voces, dict):
        raise FileNotFoundError(
            "La configuración no tiene voces válidas (campo «voces»).")
    elegida = voces.get(idioma)
    if not isinstance(elegida, dict) or not elegida.get("voz"):
        raise FileNotFoundError(
            f"No hay ninguna voz configurada para el idioma «{idioma}».")

    motor = (elegida.get("motor") or "piper").lower()
    voz = elegida["voz"]
    velocidad = cfg.get("velocidad", 1.0)
    pausa_ms = cfg.get("pausa_ms", 250)

    if motor == "piper":
        ruta = dir_lector / "voces" / "piper" / f"{voz}.onnx"
        if not ruta.is_file():
            raise _error(ruta, f"la voz Piper «{voz}»")
        log.info("Cargando Piper %s", voz)
        return PiperMotor(ruta, velocidad=velocidad, pausa_ms=pausa_ms)

    if motor == "kokoro":
        kokoro = cfg.get("kokoro") or {}
        modelo = kokoro.get("modelo") or "kokoro-v1.0.fp16.onnx"
        voces_bin = kokoro.get("voces") or "voices-v1.0.bin"
        dir_modelo = dir_lector / "modelo"
        for nombre, que in ((modelo, "el modelo Kokoro"), (voces_bin, "las voces Kokoro")):
            ruta = dir_modelo / nombre
            if not ruta.is_file():
                raise _error(ruta, que)
        log.info("Cargando Kokoro %s", voz)
        return KokoroMotor(dir_modelo, modelo, voces_bin, voz,
                           velocidad=velocidad, idioma=idioma, pausa_ms=pausa_ms)

    if motor == "chatterbox":
        log.info("Cargando Chatterbox (%s)", idioma)
        return ChatterboxMotor(idioma, pausa_ms=pausa_ms)

    if motor == "xtts":
        log.info("Cargando XTTS (%s)", voz)
        return XttsMotor(idioma, voz, pausa_ms=pausa_ms, velocidad=velocidad)

    raise ValueError(f"Motor de voz desconocido: «{motor}»")


def voces_piper_instaladas(dir_lector):
    """Nombres (sin extensión) de las voces Piper presentes, ordenados."""
    carpeta = Path(dir_lector) / "voces" / "piper"
    if not carpeta.is_dir():
        return []
    return sorted(p.stem for p in carpeta.glob("*.onnx") if p.is_file())
