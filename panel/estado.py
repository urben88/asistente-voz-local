"""Rutas y E/S atomicas del estado compartido entre el panel y el lector (spec 07).

Ficheros (runtime, no versionados), en ``<BASE>``:

  - ``estado.json``     lo escribe el panel: ``modo``, ``lector``, ``actualizado``
  - ``lector-vivo.json`` lo escribe el lector cada 2 s (aqui solo se lee)
  - ``panel.json``      configuracion del panel (copia viva)
  - ``lector/lector.json`` configuracion del lector (la edita el panel)

``BASE`` = ``%LOCALAPPDATA%\\asistente-voz-local`` (Windows) o
``${XDG_DATA_HOME:-~/.local/share}/asistente-voz-local`` (Linux).
"""

import json
import os
import sys
import time
from pathlib import Path

ES_WINDOWS = sys.platform == "win32"
PANEL_DIR = Path(__file__).resolve().parent
REPO_CONFIG = PANEL_DIR.parent / "config"


def _base_sistema():
    if ES_WINDOWS:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(local) / "asistente-voz-local"
    datos = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(datos) / "asistente-voz-local"


BASE = _base_sistema()
LECTOR_DIR = BASE / "lector"
ESTADO = BASE / "estado.json"
VIVO = BASE / "lector-vivo.json"
PANEL_JSON = BASE / "panel.json"
LECTOR_JSON = LECTOR_DIR / "lector.json"

# Handy guarda su configuración aquí (solo se lee: el panel no la toca)
def ruta_handy_settings():
    if ES_WINDOWS:
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "com.pais.handy" / "settings_store.json"
    return Path.home() / ".local" / "share" / "com.pais.handy" / "settings_store.json"

ESTADO_DEFECTO = {"lector": False}
PANEL_DEFECTO = {"atajo": "ctrl+alt+p", "handy_exe": "", "ollama_exe": "", "idioma_voz": "es"}

# Esquema de la spec 07 (R2), para cuando no hay ningun lector.json que leer
LECTOR_DEFECTO = {
    "atajo": "ctrl+alt+r",
    "idioma": "es",
    "voces": {
        "es": {"motor": "piper", "voz": "es_ES-davefx-medium"},
        "en": {"motor": "piper", "voz": "en_US-lessac-high"},
    },
    "velocidad": 1.0,
    "pausa_ms": 250,
    "max_caracteres": 20000,
    "kokoro": {"modelo": "kokoro-v1.0.fp16.onnx", "voces": "voices-v1.0.bin"},
    "ingles_xtts": True,
}

# Lector vivo con menos de estos segundos de antiguedad se considera en marcha
FRESCO_S = 6


def usar_base(base):
    """Cambia ``BASE`` y recalcula las rutas (tests con carpeta temporal)."""
    global BASE, LECTOR_DIR, ESTADO, VIVO, PANEL_JSON, LECTOR_JSON
    BASE = Path(base)
    LECTOR_DIR = BASE / "lector"
    ESTADO = BASE / "estado.json"
    VIVO = BASE / "lector-vivo.json"
    PANEL_JSON = BASE / "panel.json"
    LECTOR_JSON = LECTOR_DIR / "lector.json"


# --- E/S ---

def _leer_json(ruta):
    """dict del JSON o None si no existe / esta corrupto."""
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None


def _escribir_atomico(ruta, datos, compacto=True):
    """``ruta.tmp`` + ``os.replace``: nadie lee el fichero a medias."""
    ruta = Path(ruta)
    tmp = ruta.with_name(ruta.name + ".tmp")
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            if compacto:
                json.dump(datos, f, ensure_ascii=False)
            else:
                json.dump(datos, f, ensure_ascii=False, indent=2)
                f.write("\n")
        os.replace(tmp, ruta)
        return True
    except OSError:
        return False


# --- estado.json (panel -> lector) ---

def leer_estado():
    datos = _leer_json(ESTADO) or {}
    return {**ESTADO_DEFECTO, **datos}


def guardar_estado(lector=None):
    """Preserva lo no indicado y sella ``actualizado``.

    Solo hay un estado: el lector encendido o apagado. Los dos atajos (dictado y
    lectura) conviven siempre; no hay modos que se excluyan.
    """
    datos = leer_estado()
    datos.pop("modo", None)  # restos de la version con modos alternos
    if lector is not None:
        datos["lector"] = bool(lector)
    datos["actualizado"] = time.time()
    _escribir_atomico(ESTADO, datos)
    return datos


# --- lector.json (el panel es su editor) ---

def _migrar_lector(datos):
    """Esquema viejo (voz/modelo/voces sueltos, Kokoro) -> voces por idioma.

    Misma migracion que hace el lector al cargar, para que el panel no escriba
    una configuracion a medias si el usuario cambia algo.
    """
    if isinstance(datos.get("voces"), dict):
        return datos
    cfg = dict(datos)
    voz = cfg.pop("voz", None) or "em_alex"
    modelo = cfg.pop("modelo", None) or LECTOR_DEFECTO["kokoro"]["modelo"]
    bin_voces = cfg.pop("voces", None) or LECTOR_DEFECTO["kokoro"]["voces"]
    idioma = cfg.get("idioma") or "es"
    cfg["voces"] = {
        "es": {"motor": "kokoro", "voz": "em_alex"},
        "en": {"motor": "kokoro", "voz": "af_heart"},
    }
    cfg["voces"][idioma] = {"motor": "kokoro", "voz": voz}
    cfg["kokoro"] = {"modelo": modelo, "voces": bin_voces}
    return cfg


def leer_lector_json():
    """Config del lector instalado; si no hay, la del repo o la de defecto."""
    datos = _leer_json(LECTOR_JSON)
    if datos is None:
        datos = _leer_json(REPO_CONFIG / "lector.json")
    if datos is None:
        return json.loads(json.dumps(LECTOR_DEFECTO))
    return _migrar_lector(datos)


def guardar_lector_json(cfg):
    """Conserva todas las claves; UTF-8 sin escapar acentos, indent=2."""
    return _escribir_atomico(LECTOR_JSON, cfg, compacto=False)


# --- lector-vivo.json (lector -> panel) ---

def lector_vivo():
    return _leer_json(VIVO)


def lector_en_marcha():
    vivo = lector_vivo()
    if not vivo:
        return False
    try:
        return (time.time() - float(vivo.get("vivo", 0))) < FRESCO_S
    except (TypeError, ValueError):
        return False


# --- panel.json ---

def cargar_panel_json():
    """Config viva del panel; si no existe se crea desde la del repo o por defecto."""
    datos = _leer_json(PANEL_JSON)
    if datos is None:
        repo = _leer_json(REPO_CONFIG / "panel.json") or {}
        datos = {**PANEL_DEFECTO, **repo}
        _escribir_atomico(PANEL_JSON, datos, compacto=False)
    return {**PANEL_DEFECTO, **datos}


def guardar_panel_json(cfg):
    return _escribir_atomico(PANEL_JSON, cfg, compacto=False)


# --- Handy (solo lectura: la configuración del dictado no se toca desde el panel) ---

MODELOS_HANDY = {
    "turbo": "Whisper Turbo (large-v3-turbo)",
    "large-v3": "Whisper Large v3",
    "small": "Whisper Small",
    "medium": "Whisper Medium",
    "tiny": "Whisper Tiny",
    "cohere": "Cohere Transcribe",
}


def leer_handy_settings():
    """Ajustes de Handy que interesan al panel: modelo, idioma y atajos (o None).

    Nunca escribe: si Handy reescribe su fichero al salir, aquí no se toca nada.
    """
    datos = _leer_json(ruta_handy_settings())
    if not datos:
        return None
    ajustes = datos.get("settings") if isinstance(datos.get("settings"), dict) else {}
    modelo = str(ajustes.get("selected_model") or "")
    enlaces = ajustes.get("bindings") if isinstance(ajustes.get("bindings"), dict) else {}

    def atajo(clave):
        entrada = enlaces.get(clave) or {}
        valor = str(entrada.get("current_binding") or "")
        return valor.replace("+", " + ").replace("space", "Espacio").title() if valor else ""

    return {
        "modelo": MODELOS_HANDY.get(modelo, modelo or "desconocido"),
        "modelo_id": modelo,
        "idioma": str(ajustes.get("selected_language") or ""),
        "atajo_dictado": atajo("transcribe"),
        "atajo_asistente": atajo("transcribe_with_post_process"),
        "atajo_resumen": atajo("transcribe_with_post_process"),
        "modelo_resumen": _modelo_resumen(ajustes),
        "prompt_resumen": _prompt_resumen(ajustes),
        "resumen_activo": bool(ajustes.get("post_process_enabled")),
    }


def _modelo_resumen(ajustes):
    """Modelo de Ollama que usa Handy para el resumen/asistente."""
    proveedor = str(ajustes.get("post_process_provider_id") or "")
    modelos = ajustes.get("post_process_models") or {}
    if isinstance(modelos, dict):
        elegido = modelos.get(proveedor) or next((v for v in modelos.values() if v), "")
        if elegido:
            return str(elegido)
    return proveedor or "—"


def _prompt_resumen(ajustes):
    """Nombre del prompt de post-procesado activo (p. ej. el de resumen)."""
    activo = str(ajustes.get("post_process_selected_prompt_id") or "")
    prompts = ajustes.get("post_process_prompts") or []
    for entrada in prompts if isinstance(prompts, list) else []:
        if not isinstance(entrada, dict):
            continue
        if str(entrada.get("id") or "") == activo:
            return str(entrada.get("name") or entrada.get("id") or activo)
    return activo or "—"
