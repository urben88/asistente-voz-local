#!/usr/bin/env bash
# Funciones y constantes comunes - Asistente de voz local (Linux)
# Se carga con "source" desde install.sh, patch-config.sh y apply-config.sh.
#
# Equivalente Linux de la parte compartida de settings-merge.ps1 y de las
# utilidades de install.ps1. Estilo del repo: espanol sin tildes, salida con color.

# --- Colores (se desactivan si la salida no es un terminal) ---
if [ -t 1 ]; then
    C_RESET=$'\033[0m'; C_VERDE=$'\033[32m'; C_AMAR=$'\033[33m'
    C_ROJO=$'\033[31m'; C_CYAN=$'\033[36m'; C_GRIS=$'\033[90m'
else
    C_RESET=""; C_VERDE=""; C_AMAR=""; C_ROJO=""; C_CYAN=""; C_GRIS=""
fi

# --- Constantes del proyecto ---
MODELO_ESTANDAR="gemma4:e4b"
MODELO_LIGERO="qwen3:4b-instruct"
VRAM_MINIMA=8000

HF_REV="dfa4adebb64f3076b7b6b90b721275cc069cb421"
GGUF_SHA="14d02f1ad6dd77b3a60f82639879012c3adb4fe25c50a5a47a2c4c661daf1558"
GGUF_BYTES=1770270208

FALLOS=0
AVISOS=0
SIMULAR=0

# --- Salida ---
paso()   { printf '\n%s%s%s\n' "$C_AMAR" "$1" "$C_RESET"; }
ok()     { printf '  %sOK%s     %s\n' "$C_VERDE" "$C_RESET" "$1"; }
aviso()  { printf '  %sAVISO%s  %s\n' "$C_AMAR" "$C_RESET" "$1"; AVISOS=$((AVISOS + 1)); }
fallo()  { printf '  %sFALLO%s  %s\n' "$C_ROJO" "$C_RESET" "$1"; FALLOS=$((FALLOS + 1)); }
simula() { [ "$SIMULAR" -eq 1 ] && printf '  %sSIMULA%s %s\n' "$C_CYAN" "$C_RESET" "$1"; return 0; }
dato()   { printf '  %-18s: %s\n' "$1" "$2"; }

# --- Rutas ---
handy_cfg_dir()  { printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/com.pais.handy"; }
handy_cfg_file() { printf '%s\n' "$(handy_cfg_dir)/settings_store.json"; }
hf_base()        { printf '%s\n' "${HF_HOME:-$HOME/.cache/huggingface}/hub/models--handy-computer--cohere-transcribe-03-2026-gguf"; }
gguf_file()      { printf '%s\n' "$(hf_base)/snapshots/$HF_REV/cohere-transcribe-03-2026-Q5_K_M.gguf"; }
refs_main_file() { printf '%s\n' "$(hf_base)/refs/main"; }

# --- Comprobaciones ---
probar_puerto() { # host [puerto]
    local host="$1" puerto="${2:-443}"
    timeout 5 bash -c "exec 3<>/dev/tcp/$host/$puerto" 2>/dev/null
}

probar_ollama() {
    curl -s --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:11434/api/tags" 2>/dev/null | grep -q '^200$'
}

obtener_modelos_ollama() {
    curl -s --max-time 5 "http://127.0.0.1:11434/api/tags" 2>/dev/null \
        | python3 -c 'import json,sys
try:
    data=json.load(sys.stdin)
except Exception:
    sys.exit(0)
for m in data.get("models",[]):
    print(m.get("name",""))'
}

tiene_modelo() { # lista_texto modelo
    local lista="$1" modelo="$2"
    printf '%s\n' "$lista" | grep -qxF "$modelo" && return 0
    printf '%s\n' "$lista" | grep -qxF "$modelo:latest" && return 0
    return 1
}

obtener_vram_nvidia() {
    command -v nvidia-smi >/dev/null 2>&1 || return 1
    local salida
    salida=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null) || return 1
    [ -n "$salida" ] || return 1
    printf '%s\n' "$salida" | tr -dc '0-9\n' | sort -n | tail -1
}

handy_en_ejecucion() {
    pgrep -x handy >/dev/null 2>&1 || pgrep -f '/[Hh]andy' >/dev/null 2>&1
}

handy_ejecutable() {
    local c
    for c in \
        "$(command -v handy 2>/dev/null)" \
        "/usr/bin/handy" \
        "/usr/local/bin/handy" \
        "$HOME/.local/bin/handy" \
        "/opt/Handy/handy" \
        "/opt/handy/handy"; do
        [ -n "$c" ] && [ -x "$c" ] && { printf '%s\n' "$c"; return 0; }
    done
    return 1
}

handy_version() {
    # El binario de Handy no imprime version de forma fiable; se mira dpkg si aplica
    if dpkg -s handy >/dev/null 2>&1; then
        dpkg -s handy 2>/dev/null | awk -F': ' '/^Version:/{print $2; exit}'
    fi
}

# --- Modelo de dictado (Cohere Transcribe 2B) ---
verificar_gguf() { # path -> 0 si sha256 y tamano coinciden
    local f="$1"
    [ -f "$f" ] || return 1
    [ "$(stat -c %s "$f" 2>/dev/null)" = "$GGUF_BYTES" ] || return 1
    [ "$(sha256sum "$f" | awk '{print $1}')" = "$GGUF_SHA" ] || return 1
    return 0
}

# Devuelve 0 si el modelo de dictado queda verificado; 1 si no.
descargar_modelo_dictado() {
    local base snapshots refs gguf
    base=$(hf_base); snapshots="$(hf_base)/snapshots/$HF_REV"; refs="$(hf_base)/refs"
    gguf=$(gguf_file)
    local modelo_ok=0

    if [ -f "$gguf" ]; then
        if verificar_gguf "$gguf"; then
            ok "El modelo de dictado ya esta presente y verificado (sha256 y tamano)"
            modelo_ok=1
        else
            aviso "El modelo presente no coincide (sha256 o tamano)"
            if [ "$SIMULAR" -eq 1 ]; then
                simula "borraria el archivo y lo descargaria de nuevo"
            else
                rm -f "$gguf"
            fi
        fi
    else
        aviso "El modelo de dictado todavia no esta descargado"
    fi

    if [ "$modelo_ok" -ne 1 ]; then
        if [ "$SIMULAR" -eq 1 ]; then
            simula "descargaria el .gguf (~1,7 GB) de Hugging Face y, si falla, del mirror blob.handy.computer; verifica sha256 y tamano"
        else
            mkdir -p "$snapshots" "$refs"
            local urls=(
                "https://huggingface.co/handy-computer/cohere-transcribe-03-2026-gguf/resolve/$HF_REV/cohere-transcribe-03-2026-Q5_K_M.gguf"
                "https://blob.handy.computer/handy-computer/cohere-transcribe-03-2026-gguf/$HF_REV/cohere-transcribe-03-2026-Q5_K_M.gguf"
            )
            local url
            for url in "${urls[@]}"; do
                printf 'Descargando desde %s\n' "$url"
                if curl -L --fail --retry 3 -o "$gguf" "$url"; then
                    if verificar_gguf "$gguf"; then
                        printf 'Modelo de dictado descargado y verificado.\n'
                        modelo_ok=1
                        break
                    fi
                    printf 'AVISO: descarga incompleta o corrupta desde este origen. Se borra y se prueba el siguiente.\n'
                    rm -f "$gguf"
                else
                    printf 'AVISO: fallo la descarga desde este origen.\n'
                    rm -f "$gguf"
                fi
            done
            if [ "$modelo_ok" -ne 1 ]; then
                printf '\n%s!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!%s\n' "$C_ROJO" "$C_RESET"
                printf '%s AVISO: NO se ha podido descargar el modelo de dictado.%s\n' "$C_ROJO" "$C_RESET"
                printf '%s Sin el, Handy arrancara con OTRO modelo y el dictado no tendra%s\n' "$C_ROJO" "$C_RESET"
                printf '%s la precision esperada. Repite el instalador cuando tengas conexion.%s\n' "$C_ROJO" "$C_RESET"
                printf '%s!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!%s\n\n' "$C_ROJO" "$C_RESET"
                fallo "Modelo de dictado no descargado"
            fi
        fi
    fi

    # refs/main: Handy marca el modelo como "descargado" cuando existe este fichero
    local refs_main; refs_main=$(refs_main_file)
    if [ "$SIMULAR" -eq 1 ]; then
        if [ -f "$refs_main" ]; then
            local rev_actual; rev_actual=$(tr -d '\r\n' < "$refs_main")
            if [ "$rev_actual" = "$HF_REV" ]; then
                ok "refs/main correcto ($rev_actual)"
            else
                aviso "refs/main apunta a $rev_actual (se reescribiria con $HF_REV)"
            fi
        else
            simula "escribiria refs/main con la revision $HF_REV"
        fi
    else
        if [ "$modelo_ok" -eq 1 ]; then
            mkdir -p "$refs"
            printf '%s' "$HF_REV" > "$refs_main"
        fi
    fi

    [ "$modelo_ok" -eq 1 ] && return 0 || return 1
}
