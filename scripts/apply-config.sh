#!/usr/bin/env bash
# Re-aplicar configuracion - Asistente de voz local (Linux)
# Equivalente Linux de scripts/apply-config.ps1.
# REEMPLAZA toda la configuracion de Handy (microfono, atajos, prompts...) por la del repo
# y descarga el modelo de dictado si falta.
# Si ya tienes Handy configurado en este PC, es preferible scripts/patch-config.sh
# (solo cambia modelo de dictado, diccionario y buffer; conserva el resto).
# Requiere Handy CERRADO (bandeja del sistema -> Salir).

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
# shellcheck source=comun.sh
. "$SCRIPT_DIR/comun.sh"

REPO_CONFIG="$REPO_ROOT/config/handy-settings.json"

printf '%sAplicando configuracion del asistente de voz local...%s\n' "$C_CYAN" "$C_RESET"
printf '%sOJO: este script REEMPLAZA toda la configuracion de Handy (microfono, atajos, prompts...).%s\n' "$C_AMAR" "$C_RESET"
printf '%sSi ya tienes Handy configurado en este PC, usa mejor scripts/patch-config.sh.%s\n' "$C_AMAR" "$C_RESET"

if [ ! -f "$REPO_CONFIG" ]; then
    printf '%sAVISO: no se encuentra config/handy-settings.json%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

# --- Modelo de dictado (Cohere Transcribe 2B) en el cache de Hugging Face que lee Handy ---
descargar_modelo_dictado || true

# --- Configuracion de Handy ---
# Handy debe estar cerrado: si esta abierto, al salir reescribe el fichero y perderia el cambio
if handy_en_ejecucion; then
    printf '%sAVISO: Handy esta en ejecucion. No se ha copiado la configuracion.%s\n' "$C_AMAR" "$C_RESET"
    printf '%s Cierra Handy (bandeja -> Salir) y vuelve a ejecutar este script.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

CFG="$(handy_cfg_file)"
CFG_DIR="$(handy_cfg_dir)"
mkdir -p "$CFG_DIR"

if python3 "$SCRIPT_DIR/handy-config.py" merge --repo "$REPO_CONFIG" --live "$CFG" --full-copy; then
    printf '%sConfiguracion copiada del repo (reemplaza la anterior).%s\n' "$C_VERDE" "$C_RESET"
else
    printf '%sAVISO: no se pudo aplicar la configuracion.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

printf '%sListo. Reinicia Handy (bandeja del sistema -> salir) y vuelve a abrirlo.%s\n' "$C_VERDE" "$C_RESET"
