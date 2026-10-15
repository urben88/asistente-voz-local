#!/usr/bin/env bash
# Parche selectivo de la configuracion - Asistente de voz local (Linux)
# Equivalente Linux de scripts/patch-config.ps1.
# Copia SOLO el modelo de dictado, el diccionario (custom_words) y el buffer
# de config/handy-settings.json al Handy de ESTE PC.
# Todo lo demas (microfono, atajos, prompts...) se conserva tal cual.
# Requiere Handy CERRADO (icono de bandeja -> Salir).
#
# Uso: bash scripts/patch-config.sh
# Para un PC nuevo (instalar todo desde cero) usa scripts/install.sh.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
# shellcheck source=comun.sh
. "$SCRIPT_DIR/comun.sh"

printf '\n%s==== Parche selectivo de la configuracion de Handy ====%s\n' "$C_CYAN" "$C_RESET"
printf '%s Solo se cambian: modelo de dictado, diccionario y buffer.%s\n' "$C_CYAN" "$C_RESET"
printf '%s El resto de tu configuracion (microfono, atajos, prompts) se conserva.%s\n\n' "$C_CYAN" "$C_RESET"

# --- 1) Handy debe estar cerrado: si no, no se toca nada ---
if handy_en_ejecucion; then
    printf '%sAVISO: Handy esta en ejecucion. NO se ha tocado la configuracion.%s\n' "$C_AMAR" "$C_RESET"
    printf '%s Cierra Handy (bandeja -> Salir) y vuelve a ejecutar este script.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

# --- 2) Ficheros de origen y destino ---
SRC_CFG="$REPO_ROOT/config/handy-settings.json"
CFG="$(handy_cfg_file)"

if [ ! -f "$SRC_CFG" ]; then
    printf '%sAVISO: no se encuentra la configuracion del repo: %s%s\n' "$C_AMAR" "$SRC_CFG" "$C_RESET"
    exit 1
fi
if [ ! -f "$CFG" ]; then
    printf '%sAVISO: no se encuentra la configuracion de Handy: %s%s\n' "$C_AMAR" "$CFG" "$C_RESET"
    printf '%s Este script es para un PC ya configurado. En un PC nuevo usa scripts/install.sh.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

# --- 3) Merge selectivo (logica compartida en scripts/handy-config.py) ---
if ! python3 "$SCRIPT_DIR/handy-config.py" merge --repo "$SRC_CFG" --live "$CFG"; then
    printf '%sAVISO: no se pudo aplicar el parche.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

printf '\n%sListo. Abre Handy y comprueba en Ajustes que el modelo es Cohere Transcribe.%s\n' "$C_VERDE" "$C_RESET"
