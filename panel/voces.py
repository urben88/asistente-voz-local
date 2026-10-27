"""Catalogo curado de voces e instalacion de voces Piper (spec 07, R7).

Piper se instala con ``python -m piper.download_voices`` usando el interprete del
venv del lector; las voces quedan en ``<dir_lector>/voces/piper/<voz>.onnx``.
Kokoro son voces del bin curado (no se descargan: vienen con el modelo).
"""

import logging
import subprocess
from pathlib import Path

try:
    from . import control
except ImportError:  # ejecutado como script suelto desde panel/
    import control

log = logging.getLogger("panel.voces")

# Catalogo curado (spec R7). Los datos de calidad, tamano, carga y velocidad estan
# medidos en este PC y son los que muestra la guia «¿Qué elijo?» (panel/ayuda.py).
CATALOGO = {
    "es": [
        {"id": "es_MX-claude-high", "idioma": "es", "descripcion": "Hombre · México · calidad alta",
         "mb": 60, "calidad": "alta", "acento": "México", "sexo": "hombre",
         "carga_s": 2.4, "rtf": "37× tiempo real", "orden": 1,
         "nota": "La más natural en español; acento mexicano neutro y muy claro."},
        {"id": "es_ES-sharvard-medium", "idioma": "es", "descripcion": "Hombre y mujer · España · calidad media",
         "mb": 73, "calidad": "media", "acento": "España", "sexo": "hombre y mujer",
         "carga_s": 3.6, "rtf": "33× tiempo real", "orden": 2,
         "nota": "La mejor de España: dos voces (hombre y mujer) en una."},
        {"id": "es_ES-davefx-medium", "idioma": "es", "descripcion": "Hombre · España · calidad media",
         "mb": 60, "calidad": "media", "acento": "España", "sexo": "hombre",
         "carga_s": 5.6, "rtf": "31× tiempo real", "orden": 3,
         "nota": "La más ligera y rápida del español; algo menos natural."},
        {"id": "es_AR-daniela-high", "idioma": "es", "descripcion": "Mujer · Argentina · calidad alta",
         "mb": 114, "calidad": "alta", "acento": "Argentina", "sexo": "mujer",
         "carga_s": 4.0, "rtf": "~20× tiempo real (estimado)", "orden": 4,
         "nota": "Acento argentino, voz femenina y calidad alta."},
    ],
    "en": [
        {"id": "en_US-lessac-high", "idioma": "en", "descripcion": "Mujer · EE. UU. · calidad alta",
         "mb": 109, "calidad": "alta", "acento": "EE. UU.", "sexo": "mujer",
         "carga_s": 4.2, "rtf": "6,6× tiempo real", "orden": 1,
         "nota": "La más natural de inglés; referencia para EE. UU."},
        {"id": "en_US-ryan-high", "idioma": "en", "descripcion": "Hombre · EE. UU. · calidad alta",
         "mb": 114, "calidad": "alta", "acento": "EE. UU.", "sexo": "hombre",
         "carga_s": 4.0, "rtf": "~7× tiempo real (estimado)", "orden": 2,
         "nota": "Inglés estadounidense masculino, calidad alta."},
        {"id": "en_GB-cori-high", "idioma": "en", "descripcion": "Mujer · R. U. · calidad alta",
         "mb": 114, "calidad": "alta", "acento": "R. U.", "sexo": "mujer",
         "carga_s": 4.0, "rtf": "~7× tiempo real (estimado)", "orden": 3,
         "nota": "Inglés británico femenino, calidad alta."},
        {"id": "en_US-amy-medium", "idioma": "en", "descripcion": "Mujer · EE. UU. · calidad media",
         "mb": 60, "calidad": "media", "acento": "EE. UU.", "sexo": "mujer",
         "carga_s": 3.3, "rtf": "26× tiempo real", "orden": 4,
         "nota": "La más rápida y ligera del inglés; media pero muy buena."},
    ],
}

# Datos de Kokoro para la guia comparativa (no se descargan: van con el modelo)
KOKORO_INFO = {
    "es": {
        "voces": ["em_alex", "ef_dora", "em_santa"],
        "acento": "Español neutro",
        "sexo": "hombre y mujer",
        "calidad": "básica",
        "carga_s": 2.8,
        "rtf": "3,6× tiempo real",
        "ram_mb": 450,
        "nota": "Un solo modelo para todo; en español solo hay 3 voces y suena más plano.",
    },
    "en": {
        "voces": ["af_heart"],
        "acento": "Inglés neutro",
        "sexo": "mujer",
        "calidad": "alta",
        "carga_s": 2.8,
        "rtf": "3,6× tiempo real",
        "ram_mb": 450,
        "nota": "Su punto fuerte: af_heart es natural y sirve para todo con un solo motor.",
    },
}

KOKORO = {
    "es": ["em_alex", "ef_dora", "em_santa"],
    "en": ["af_heart", "am_michael", "af_bella", "am_onyx"],
}

# Motores de alta calidad (GPU). Sus voces van con el motor (no se descargan aparte).
VOCES_CALIDAD = {
    "es": {
        "chatterbox": ["por defecto"],
        "xtts": ["Luis Moray", "Eugenio Matarací", "Alma María", "Marcos Rudaski"],
    },
    "en": {
        "chatterbox": ["por defecto"],
        "xtts": ["Claribel Dervla", "Damien Black", "Craig Gutsy", "Sofia Hellen"],
    },
}

INFO_CALIDAD = {
    "chatterbox": {
        "calidad": "alta", "vram_gb": 3.2,
        "rtf": "1,3× tiempo real (genera más lento de lo que habla)",
        "nota": "La más natural en español, pero puede hacer pausas entre frases.",
    },
    "xtts": {
        "calidad": "alta", "vram_gb": 1.8,
        "rtf": "1,6× más rápido que el tiempo real",
        "nota": "58 voces y 17 idiomas; acento neutro tirando a latinoamericano.",
    },
}


def voces_calidad(idioma, motor):
    return list((VOCES_CALIDAD.get(idioma) or {}).get(motor, []))


# Voz recomendada por motor e idioma (la que mejor equilibra calidad y velocidad)
RECOMENDADAS = {
    "piper": {"es": "es_MX-claude-high", "en": "en_US-lessac-high"},
    "xtts": {"es": "Luis Moray", "en": "Claribel Dervla"},
    "chatterbox": {"es": "por defecto", "en": "por defecto"},
    "kokoro": {"es": "em_alex", "en": "af_heart"},
}

# Motor recomendado segun haya GPU o no, con el motivo que se muestra en el panel
RECOMENDACION_MOTOR = {
    "xtts": ("XTTS", "mejor calidad y velocidad con tu GPU (1,8 GB): 1,6× más rápido "
                     "que el tiempo real, sin pausas y deja sitio al dictado."),
    "piper": ("Piper", "el más rápido y ligero (CPU, 30×): no usa GPU, no afecta al "
                       "dictado y no hace pausas."),
    "chatterbox": ("Chatterbox", "la voz más natural, pero deja la GPU sin memoria: el dictado "
                                 "puede ir lento."),
    "kokoro": ("Kokoro", "alternativa en CPU; su punto fuerte es el inglés."),
}


def motor_recomendado(hay_gpu=True):
    return "xtts" if hay_gpu else "piper"


def recomendada(motor, idioma):
    return (RECOMENDADAS.get((motor or "piper").lower()) or {}).get(idioma or "es", "")


def etiqueta_voz(nombre, motor, idioma):
    """Nombre para el desplegable, con estrella si es la voz recomendada."""
    return f"★ {nombre}" if nombre and nombre == recomendada(motor, idioma) else nombre


def catalogo(idioma):
    """Entradas curadas del idioma (copia, para que la UI no lo modifique)."""
    return [dict(v) for v in CATALOGO.get(idioma, [])]


def voces_kokoro(idioma):
    return list(KOKORO.get(idioma, []))


def _dir_piper(dir_lector):
    return Path(dir_lector) / "voces" / "piper"


def instaladas(dir_lector, motor, idioma):
    """Voces disponibles para ese motor e idioma, ordenadas.

    Piper: ficheros ``voces/piper/*.onnx`` cuyo prefijo es el idioma (``es_``/``en_``).
    Kokoro: lista curada del bin (no se puede introspeccionar sin cargarlo).
    """
    motor = (motor or "piper").lower()
    if motor == "kokoro":
        return voces_kokoro(idioma)
    if motor in INFO_CALIDAD:
        return voces_calidad(idioma, motor)
    carpeta = _dir_piper(dir_lector)
    if not carpeta.is_dir():
        return []
    prefijo = f"{idioma}_"
    return sorted(p.stem for p in carpeta.glob("*.onnx")
                  if p.is_file() and p.stem.lower().startswith(prefijo))


def tamano_mb_instalada(voz, dir_lector):
    ruta = _dir_piper(dir_lector) / f"{voz}.onnx"
    try:
        return round(ruta.stat().st_size / 1_000_000, 1)
    except OSError:
        return None


def descargar(voz, dir_lector, progreso=None):
    """Descarga una voz Piper. Devuelve (ok, mensaje); nunca lanza.

    ``progreso(texto)`` se llama con mensajes para la etiqueta de la ventana.
    """
    avisar = progreso or (lambda _texto: None)
    python = control.python_venv()
    if not Path(python).is_file():
        return False, f"No encuentro el Python del lector en {python}"
    destino = _dir_piper(dir_lector)
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return False, f"No se pudo crear {destino}: {e}"

    avisar(f"Descargando {voz}… si tarda, sigue en segundo plano")
    cmd = [str(python), "-m", "piper.download_voices", "--download-dir", str(destino), voz]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=900, creationflags=control.CREATE_NO_WINDOW if control.ES_WINDOWS else 0,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("Fallo descargando %s: %s", voz, e)
        return False, f"No se pudo descargar {voz}: {e}"

    onnx = destino / f"{voz}.onnx"
    json_voz = destino / f"{voz}.onnx.json"
    if r.returncode != 0 or not onnx.is_file() or not json_voz.is_file():
        detalle = (r.stderr or r.stdout or "").strip().splitlines()
        detalle = detalle[-1] if detalle else f"codigo {r.returncode}"
        log.warning("Descarga de %s fallida: %s", voz, detalle)
        return False, f"No se pudo descargar {voz}: {detalle}"
    return True, f"{voz} instalada"
