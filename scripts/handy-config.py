#!/usr/bin/env python3
# Merge de configuracion de Handy (Linux) - Asistente de voz local
#
# Equivalente Linux de scripts/settings-merge.ps1. Copia SOLO selected_model,
# custom_words y extra_recording_buffer_ms de config/handy-settings.json al
# settings real de Handy, conservando el resto (microfono, atajos, prompts...).
# Con --full-copy escribe el fichero entero del repo (PC nuevo, sin configuracion).
#
# Cuidados obligatorios:
#   - UTF-8 SIN BOM, con acentos intactos (los prompts y el microfono llevan tildes).
#   - Copia previa settings_store.json.bak.
#   - Verificacion posterior: mismo microfono, mismos prompts y mismo numero de claves.
#
# El llamador debe comprobar ANTES que Handy esta cerrado (si no, lo reescribe al salir).

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

MODELO_ESTANDAR = "gemma4:e4b"

# En Linux Handy usa por defecto el gestor de atajos de Tauri (global-shortcut),
# que no necesita leer /dev/input. El config del repo trae "handy_keys" (default de
# Windows), que en Linux exige pertenecer al grupo 'input'. Por eso en Linux se
# fuerza "tauri" (equivalente al default de Handy en Linux).
KEYBOARD_IMPL_LINUX = "tauri"

# En Linux el pegador por defecto de Handy es "direct" (teclea el texto en el cursor),
# que funciona tambien donde Ctrl+V no lo hace (terminales, algunos Electron...).
# El config del repo trae "ctrl_v" (default de Windows). Se puede cambiar en Ajustes.
PASTE_METHOD_LINUX = "direct"


def leer_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def escribir_json(path, data):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def merge(repo_path, live_path, assistant_model="", full_copy=False, solo_dictado=False):
    src = leer_json(repo_path)
    res = {
        "ok": False,
        "full_copy": bool(full_copy),
        "backup": "",
        "selected_model": "",
        "custom_words": 0,
        "buffer": 0,
        "mic_before": "",
        "mic_after": "",
        "prompts_before": 0,
        "prompts_after": 0,
        "keys_before": 0,
        "keys_after": 0,
        "assistant_model": "",
        "keyboard_impl": "",
        "paste_method": "",
        "post_process_enabled": None,
        "error": "",
    }

    src_settings = src.get("settings", {})

    if full_copy:
        dest = copy.deepcopy(src)
    else:
        if not Path(live_path).exists():
            res["error"] = "No existe la configuracion de Handy: %s" % live_path
            return res
        dest = leer_json(live_path)

    dest_settings = dest.setdefault("settings", {})

    esperado_modelo = src_settings.get("selected_model")
    esperado_palabras = len(src_settings.get("custom_words") or [])
    esperado_buffer = src_settings.get("extra_recording_buffer_ms")

    res["mic_before"] = dest_settings.get("selected_microphone")
    res["prompts_before"] = len(dest_settings.get("post_process_prompts") or [])
    res["keys_before"] = len(dest_settings.keys())

    if Path(live_path).exists():
        shutil.copyfile(live_path, live_path + ".bak")
        res["backup"] = live_path + ".bak"
        print("Copia de seguridad: settings_store.json.bak")

    dest_settings["selected_model"] = esperado_modelo
    dest_settings["custom_words"] = list(src_settings.get("custom_words") or [])
    dest_settings["extra_recording_buffer_ms"] = esperado_buffer
    dest_settings["keyboard_implementation"] = KEYBOARD_IMPL_LINUX
    dest_settings["paste_method"] = PASTE_METHOD_LINUX
    if solo_dictado:
        # Solo transcripcion: se desactiva el post-procesado (IA). El dictado no lo necesita.
        dest_settings["post_process_enabled"] = False
    elif assistant_model and assistant_model != MODELO_ESTANDAR:
        dest_settings.setdefault("post_process_models", {})["custom"] = assistant_model

    escribir_json(live_path, dest)

    final = leer_json(live_path).get("settings", {})
    res["selected_model"] = final.get("selected_model")
    res["custom_words"] = len(final.get("custom_words") or [])
    res["buffer"] = final.get("extra_recording_buffer_ms")
    res["mic_after"] = final.get("selected_microphone")
    res["prompts_after"] = len(final.get("post_process_prompts") or [])
    res["keys_after"] = len(final.keys())
    res["assistant_model"] = (final.get("post_process_models") or {}).get("custom", "")
    res["keyboard_impl"] = final.get("keyboard_implementation")
    res["paste_method"] = final.get("paste_method")
    res["post_process_enabled"] = final.get("post_process_enabled")

    print("")
    print("Aplicado:")
    print("  selected_model            : %s" % res["selected_model"])
    print("  extra_recording_buffer_ms : %s" % res["buffer"])
    print("  keyboard_implementation   : %s" % res["keyboard_impl"])
    print("  paste_method              : %s" % res["paste_method"])
    print("  post_process_enabled      : %s" % res["post_process_enabled"])
    print("  custom_words (%d): %s" % (res["custom_words"], ", ".join(final.get("custom_words") or [])))
    if assistant_model and not solo_dictado:
        print("  post_process_models.custom: %s" % res["assistant_model"])
    if not full_copy:
        print("Conservado:")
        print("  selected_microphone       : %s" % res["mic_after"])
        print("  post_process_prompts      : %s (antes %s)" % (res["prompts_after"], res["prompts_before"]))
        print("  claves de settings        : %s (antes %s)" % (res["keys_after"], res["keys_before"]))

    ok = (
        res["selected_model"] == esperado_modelo
        and res["custom_words"] == esperado_palabras
        and         res["buffer"] == esperado_buffer
        and res["keyboard_impl"] == KEYBOARD_IMPL_LINUX
        and res["paste_method"] == PASTE_METHOD_LINUX
    )
    if not full_copy:
        ok = ok and res["mic_after"] == res["mic_before"]
        ok = ok and res["prompts_after"] == res["prompts_before"]
        ok = ok and res["keys_after"] == res["keys_before"]
    if solo_dictado:
        ok = ok and res["post_process_enabled"] is False
    elif assistant_model:
        ok = ok and res["assistant_model"] == assistant_model

    if not ok:
        res["error"] = "El resultado no coincide con lo esperado."
        print("AVISO: algo mas cambio y no deberia. Restaura settings_store.json.bak si falta algun ajuste.", file=sys.stderr)
    res["ok"] = ok
    return res


def resumen(live_path):
    try:
        s = leer_json(live_path).get("settings", {})
    except Exception as exc:  # noqa: BLE001
        print("No se pudo leer %s: %s" % (live_path, exc))
        return 1
    print("  selected_model            : %s" % s.get("selected_model"))
    print("  extra_recording_buffer_ms : %s" % s.get("extra_recording_buffer_ms"))
    print("  keyboard_implementation   : %s" % s.get("keyboard_implementation"))
    print("  post_process_enabled      : %s" % s.get("post_process_enabled"))
    print("  custom_words              : %s" % len(s.get("custom_words") or []))
    print("  selected_microphone       : %s" % s.get("selected_microphone"))
    print("  post_process_prompts      : %s" % len(s.get("post_process_prompts") or []))
    print("  post_process_models.custom: %s" % (s.get("post_process_models") or {}).get("custom", ""))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Merge de configuracion de Handy (Linux)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_merge = sub.add_parser("merge", help="aplica la configuracion del repo al settings real")
    p_merge.add_argument("--repo", required=True)
    p_merge.add_argument("--live", required=True)
    p_merge.add_argument("--assistant-model", default="")
    p_merge.add_argument("--full-copy", action="store_true")
    p_merge.add_argument("--solo-dictado", action="store_true")

    p_show = sub.add_parser("show", help="muestra un resumen del settings real")
    p_show.add_argument("--live", required=True)

    args = parser.parse_args()

    if args.cmd == "show":
        return resumen(args.live)

    res = merge(args.repo, args.live, args.assistant_model, args.full_copy, args.solo_dictado)
    if res["error"]:
        print("ERROR: %s" % res["error"], file=sys.stderr)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
