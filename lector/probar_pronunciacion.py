"""Prueba de oido de la pronunciacion (spec 17, R10).

Genera con XTTS tres WAV de la misma frase mezclada y dice cuanto tarda cada uno:
  1_sin_preparar.wav   texto tal cual, todo en espanol
  2_preparada.wav      anglicismos, siglas y numeros reescritos (sin cambio de idioma)
  3_con_ingles.wav     ademas, los tramos en ingles dichos en ingles

Uso:  python probar_pronunciacion.py <carpeta> ["frase"]
Necesita la GPU libre: si el lector residente la ocupa, paralo antes.
"""

import json
import sys
import time
import wave
from pathlib import Path

import numpy as np

from motor import XttsMotor
from lector import trocear
from pronunciar import generar, segmentos

FRASE = ("Claude dijo: you should run the tests first. Luego haz commit y push del README "
         "en GitHub; la API usa 8 GB de VRAM y tarda 12,5 segundos con la v2.1.")


def guardar(ruta, audio, sr):
    datos = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(datos.tobytes())


def main():
    carpeta = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    carpeta.mkdir(parents=True, exist_ok=True)
    frase = sys.argv[2] if len(sys.argv) > 2 else FRASE
    cfg = json.loads((Path(__file__).parent / "lector.json").read_text(encoding="utf-8")) \
        if (Path(__file__).parent / "lector.json").is_file() else {}
    voz = (cfg.get("voces", {}).get("es") or {}).get("voz", "Luis Moray")
    motor = XttsMotor("es", voz)
    motor.crear("Hola.")  # calentar

    pruebas = (
        ("1_sin_preparar", [(frase, "es")]),
        ("2_preparada", segmentos(frase, "es", ingles=False)),
    )
    for nombre, partes in pruebas:
        inicio = time.monotonic()
        audio = motor.crear_segmentos(partes)
        tarda = time.monotonic() - inicio
        guardar(carpeta / f"{nombre}.wav", audio, motor.sr)
        print(f"{nombre}: genera {tarda:.1f} s, dura {len(audio) / motor.sr:.1f} s")
        for texto, idioma in partes:
            print(f"   [{idioma}] {texto}")

    # Variante 3 por el mismo camino que Ctrl+Alt+R: trocear + generar
    inicio = time.monotonic()
    trozos = []
    for frase in trocear(frase):
        audio = generar(motor, frase, "es", ingles=True)
        if audio is not None:
            trozos.append(audio)
        print("   " + " | ".join(f"[{i}] {t}" for t, i in segmentos(frase, "es", ingles=True)))
    audio = np.concatenate(trozos)
    guardar(carpeta / "3_con_ingles.wav", audio, motor.sr)
    print(f"3_con_ingles: genera {time.monotonic() - inicio:.1f} s, dura {len(audio) / motor.sr:.1f} s")


if __name__ == "__main__":
    main()
