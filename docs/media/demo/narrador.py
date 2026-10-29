#!/usr/bin/env python
"""Narra las escenas de la demo con un motor de voz del propio proyecto.

Reutiliza ``lector/motor.py`` (``cargar_motor``) del entorno del lector, así que
XTTS, Chatterbox, Piper, Kokoro o Supertonic suenan exactamente como en el
asistente, con la misma limpieza de bordes y las mismas pausas.

Uso (desde el venv del lector):

    python narrador.py --textos textos.json --salida ./voz --motor xtts --voz "Luis Moray"

``textos.json`` es una lista de cadenas; escribe ``voz_0.wav``, ``voz_1.wav``…
en la carpeta de salida (PCM 16 bits, la frecuencia del motor).

XTTS y Chatterbox **no son modelos de Ollama**: son motores de texto a voz que
se instalan en el entorno del lector con ``lector/requirements-calidad.txt``.
"""

import argparse
import json
import os
import sys
import wave
from pathlib import Path

import numpy as np


def carpeta_lector(indicada):
    """Encuentra la carpeta del lector (la instalada o la del repositorio)."""
    candidatas = []
    if indicada:
        candidatas.append(Path(indicada))
    if os.environ.get("LECTOR_DIR"):
        candidatas.append(Path(os.environ["LECTOR_DIR"]))
    local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    candidatas.append(Path(local) / "asistente-voz-local" / "lector")
    candidatas.append(Path(__file__).resolve().parents[3] / "lector")
    for c in candidatas:
        if (c / "motor.py").is_file():
            return c
    raise SystemExit("No encuentro lector/motor.py (usa --lector /ruta/al/lector)")


def escribir_wav(ruta, audio, sr):
    datos = np.clip(np.asarray(audio, dtype=np.float32).reshape(-1), -1.0, 1.0)
    pcm = (datos * 32767.0).astype("<i2")
    with wave.open(str(ruta), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(int(sr))
        f.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser(description="Narra los textos de la demo")
    ap.add_argument("--textos", required=True, help="JSON con la lista de textos")
    ap.add_argument("--salida", required=True, help="carpeta donde dejar voz_N.wav")
    ap.add_argument("--motor", default="xtts", help="xtts | chatterbox | piper | kokoro | supertonic")
    ap.add_argument("--voz", default="Luis Moray")
    ap.add_argument("--idioma", default="es")
    ap.add_argument("--velocidad", type=float, default=1.0)
    ap.add_argument("--lector", default=None, help="carpeta del lector (con motor.py)")
    args = ap.parse_args()

    textos = json.loads(Path(args.textos).read_text(encoding="utf-8"))
    if not isinstance(textos, list) or not textos:
        raise SystemExit("El JSON tiene que ser una lista de textos no vacía")

    dir_lector = carpeta_lector(args.lector)
    sys.path.insert(0, str(dir_lector))
    import motor as motores  # noqa: E402  (depende del sys.path de arriba)

    cfg = {
        "idioma": args.idioma,
        "voces": {args.idioma: {"motor": args.motor, "voz": args.voz}},
        "velocidad": args.velocidad,
        "pausa_ms": 120,
    }
    print(f"motor {args.motor} · voz {args.voz} · idioma {args.idioma}", flush=True)
    voz = motores.cargar_motor(cfg, dir_lector)

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    for i, texto in enumerate(textos):
        audio = voz.crear(texto)
        destino = salida / f"voz_{i}.wav"
        escribir_wav(destino, audio, voz.sr)
        segundos = len(audio) / float(voz.sr)
        print(f"  · {i}: {segundos:.2f} s  ({len(texto)} caracteres)", flush=True)
    print("listo", flush=True)


if __name__ == "__main__":
    main()
