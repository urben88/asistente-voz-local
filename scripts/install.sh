#!/usr/bin/env bash
# Instalador - Asistente de voz local (Handy + Ollama) para Linux
# Equivalente Linux de scripts/install.ps1.
#
# Uso recomendado: ./Instalar.sh   (o: bash scripts/install.sh)
#
# Opciones:
#   --simular             solo comprueba la maquina y explica lo que haria
#                         (no instala, no descarga, no copia y no toca la configuracion)
#   --solo-dictado        SOLO transcripcion: no instala Ollama ni modelos de IA
#                         (alias: --sin-ia). Se activa solo si no hay GPU NVIDIA.
#   --modelo <modelo>     fuerza el modelo de texto del asistente (p. ej. qwen3:4b-instruct)
#   --no-abrir            no ofrece abrir Handy al terminar
#   --metodo <modo>       como instalar Handy: auto | deb | appimage (por defecto: auto)
#   --sin-lector          no instala el lector de voz (fase 6, Kokoro)
#
# Requiere Handy CERRADO (icono de bandeja -> Salir).

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
# shellcheck source=comun.sh
. "$SCRIPT_DIR/comun.sh"

REPO_CONFIG="$REPO_ROOT/config/handy-settings.json"
ASISTENTE_MODELO=""
NO_ABRIR=0
METODO="auto"
SOLO_DICTADO=0
SIN_LECTOR=0

uso() {
    sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
}

# --- Argumentos ---
while [ $# -gt 0 ]; do
    case "$1" in
        --simular) SIMULAR=1 ;;
        --no-abrir) NO_ABRIR=1 ;;
        --solo-dictado|--sin-ia) SOLO_DICTADO=1 ;;
        --sin-lector) SIN_LECTOR=1 ;;
        --modelo) ASISTENTE_MODELO="${2:-}"; shift ;;
        --metodo) METODO="${2:-}"; shift ;;
        -h|--ayuda|--help) uso; exit 0 ;;
        *) printf 'Opcion no reconocida: %s (usa --ayuda)\n' "$1" >&2; exit 1 ;;
    esac
    shift
done

# =====================================================================
#  Acciones de instalacion
# =====================================================================

# URL del asset de Handy en la ultima release (deb o appimage) para esta arquitectura
url_asset_handy() { # deb|appimage
    local tipo="$1" tmp
    tmp="$(mktemp)" || return 1
    if ! curl -sL "https://api.github.com/repos/cjpais/Handy/releases/latest" -o "$tmp"; then
        rm -f "$tmp"; return 1
    fi
    python3 -c '
import json, sys
tipo, arq, path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    data = json.load(open(path))
except Exception:
    sys.exit(1)
suffix = ".deb" if tipo == "deb" else ".AppImage"
tokens = ["amd64", "x86_64"] if arq in ("x86_64", "amd64") else ["arm64", "aarch64"]
for a in data.get("assets", []):
    n = a.get("name", "")
    if n.endswith(suffix) and any(t in n for t in tokens):
        print(a["browser_download_url"]); break
' "$tipo" "$ARQ" "$tmp"
    rm -f "$tmp"
}

instalar_handy_deb() {
    local url="$1" tmp rc
    [ -n "$url" ] || { printf 'No se encontro el .deb de Handy\n'; return 1; }
    tmp="$(mktemp --suffix=.deb)" || return 1
    printf '  Descargando Handy (.deb)...\n'
    if ! curl -L --fail -o "$tmp" "$url"; then rm -f "$tmp"; return 1; fi
    if [ "$(id -u)" -eq 0 ]; then
        apt-get install -y "$tmp"
    else
        sudo apt-get install -y "$tmp"
    fi
    rc=$?
    rm -f "$tmp"
    return $rc
}

instalar_handy_appimage() {
    local url="$1" dest="$HOME/.local/bin/handy" tmp
    [ -n "$url" ] || { printf 'No se encontro el AppImage de Handy\n'; return 1; }
    mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
    tmp="$(mktemp)" || return 1
    printf '  Descargando Handy (AppImage)...\n'
    if ! curl -L --fail -o "$tmp" "$url"; then rm -f "$tmp"; return 1; fi
    chmod +x "$tmp"
    mv -f "$tmp" "$dest"
    cat > "$HOME/.local/share/applications/handy.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Handy
Comment=Dictado por voz local
Exec=env APPIMAGE_EXTRACT_AND_RUN=1 $dest
Terminal=false
Categories=Utility;Accessibility;
EOF
    printf '  Handy instalado en %s\n' "$dest"
    return 0
}

instalar_handy() {
    local url
    case "$METODO" in
        deb)
            url="$(url_asset_handy deb)"; instalar_handy_deb "$url" || return 1 ;;
        appimage)
            url="$(url_asset_handy appimage)"; instalar_handy_appimage "$url" || return 1 ;;
        auto)
            if command -v apt-get >/dev/null 2>&1 && { [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null || [ -t 0 ]; }; then
                url="$(url_asset_handy deb)"
                if [ -n "$url" ] && instalar_handy_deb "$url"; then return 0; fi
                printf '  El .deb fallo; se intenta con AppImage...\n'
            fi
            url="$(url_asset_handy appimage)"
            instalar_handy_appimage "$url" || return 1 ;;
        *)
            printf 'Metodo no valido: %s\n' "$METODO"; return 1 ;;
    esac
    HANDY_EXE="$(handy_ejecutable)" || true
    return 0
}

arrancar_ollama() {
    # 1) servicio systemd del sistema (si existe y tenemos permisos)
    if systemctl list-unit-files 2>/dev/null | grep -q '^ollama\.service'; then
        if [ "$(id -u)" -eq 0 ]; then
            systemctl start ollama 2>/dev/null && return 0
        elif sudo -n systemctl start ollama 2>/dev/null; then
            return 0
        fi
    fi
    # 2) 'ollama serve' en segundo plano como usuario
    if command -v ollama >/dev/null 2>&1; then
        nohup ollama serve >"${TMPDIR:-/tmp}/ollama-serve.log" 2>&1 &
        return 0
    fi
    return 1
}

# --- Lector de voz (Kokoro) ---
LECTOR_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/asistente-voz-local/lector"
LECTOR_URL_BASE="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
# nombre:bytes:sha256
LECTOR_ARCHIVOS=(
    "kokoro-v1.0.fp16.onnx:163527961:f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96"
    "voices-v1.0.bin:28214398:bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
)

verificar_archivo() { # ruta bytes sha256 -> 0 si tamano y sha256 coinciden
    [ -f "$1" ] || return 1
    [ "$(stat -c %s "$1" 2>/dev/null)" = "$2" ] || return 1
    [ "$(sha256sum "$1" | awk '{print $1}')" = "$3" ] || return 1
}

buscar_uv() {
    if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
    [ -x "$HOME/.local/bin/uv" ] && { printf '%s\n' "$HOME/.local/bin/uv"; return 0; }
    return 1
}

lector_en_marcha() { pgrep -f "$LECTOR_DIR/lector.py" >/dev/null 2>&1; }

# =====================================================================
#  Cabecera
# =====================================================================

printf '\n%s===============================================%s\n' "$C_CYAN" "$C_RESET"
printf '%s  Asistente de voz local - Instalador Linux    %s\n' "$C_CYAN" "$C_RESET"
printf '%s===============================================%s\n' "$C_CYAN" "$C_RESET"
if [ "$SIMULAR" -eq 1 ]; then
    printf '%s  MODO SIMULACION: no se instala, no se descarga y no se toca nada%s\n' "$C_CYAN" "$C_RESET"
else
    printf '%s  Instalacion real en este PC%s\n' "$C_CYAN" "$C_RESET"
fi

if [ ! -f "$REPO_CONFIG" ]; then
    printf '\n%sNo se encuentra config/handy-settings.json.%s\n' "$C_ROJO" "$C_RESET"
    printf '%sEjecuta el instalador desde la carpeta completa del repositorio.%s\n' "$C_AMAR" "$C_RESET"
    exit 1
fi

# =====================================================================
#  Preflight
# =====================================================================

paso "[0/6] Comprobaciones previas"

# --- SO de 64 bits y distro ---
ARQ="$(uname -m)"
case "$ARQ" in
    x86_64|amd64) ok "Sistema: Linux $ARQ (64 bits)" ;;
    aarch64|arm64) ok "Sistema: Linux $ARQ (64 bits)" ;;
    *) aviso "Arquitectura $ARQ; se recomienda una distro de 64 bits (x86_64/aarch64)" ;;
esac

DISTRO_ID="desconocida"
if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    DISTRO_ID="$(. /etc/os-release; printf '%s' "${ID:-desconocida}")"
    DISTRO_LIKE="$(. /etc/os-release; printf '%s' "${ID_LIKE:-}")"
    PRETTY="$(. /etc/os-release; printf '%s' "${PRETTY_NAME:-$DISTRO_ID}")"
else
    DISTRO_LIKE=""
    PRETTY="$DISTRO_ID"
fi
if printf '%s %s' "$DISTRO_ID" "$DISTRO_LIKE" | grep -qiE 'debian|ubuntu|mint'; then
    ok "Distro: $PRETTY (paquetes .deb compatibles)"
else
    aviso "Distro: $PRETTY. Se asume paqueteria .deb; si no, usa --metodo appimage"
fi

# --- Espacio libre ---
LIBRE_KB=$(df -Pk "$HOME" 2>/dev/null | awk 'NR==2{print $4}')
LIBRE_GB=""
[ -n "$LIBRE_KB" ] && LIBRE_GB=$(LC_ALL=C awk "BEGIN{printf \"%.1f\", $LIBRE_KB/1024/1024}")
if [ -z "$LIBRE_GB" ]; then
    aviso "No se ha podido comprobar el espacio libre en $HOME"
elif LC_ALL=C awk "BEGIN{exit !($LIBRE_GB < 20)}"; then
    aviso "Quedan solo $LIBRE_GB GB libres (se recomiendan 20 GB)"
    if [ "$SIMULAR" -eq 1 ]; then
        simula "preguntaria: Continuar de todas formas? (s/n)"
    else
        printf 'Continuar de todas formas? (s/n) '
        read -r respuesta
        case "$respuesta" in
            s|S|si|SI|Si) ;;
            *) printf '%sInstalacion cancelada por falta de espacio.%s\n' "$C_AMAR" "$C_RESET"; exit 1 ;;
        esac
    fi
else
    ok "Espacio libre en \$HOME: $LIBRE_GB GB"
fi

# --- Conectividad basica (avisa, no bloquea) ---
NET_HF=0; NET_OLLAMA=0
probar_puerto huggingface.co 443 && NET_HF=1
probar_puerto ollama.com 443 && NET_OLLAMA=1
if [ "$NET_HF" -eq 1 ]; then ok "Conectividad: huggingface.co accesible"
else aviso "No se puede acceder a huggingface.co (se intentara el mirror para el modelo de dictado)"; fi
if [ "$NET_OLLAMA" -eq 1 ]; then ok "Conectividad: ollama.com accesible"
else aviso "No se puede acceder a ollama.com (no se podran descargar los modelos del asistente)"; fi

if [ "$SIN_LECTOR" -eq 0 ]; then
    if probar_puerto github.com 443; then ok "Conectividad: github.com accesible"
    else aviso "No se puede acceder a github.com (no se podra descargar el modelo del lector de voz)"; fi
fi

# --- Handy NO en ejecucion ---
if handy_en_ejecucion; then
    printf '\n%sHandy esta ABIERTO.%s\n' "$C_ROJO" "$C_RESET"
    printf '%sHay que cerrarlo antes de instalar, porque Handy reescribe su configuracion al salir:%s\n' "$C_AMAR" "$C_RESET"
    printf '%s  icono de Handy en la bandeja -> clic derecho -> Salir%s\n' "$C_AMAR" "$C_RESET"
    printf '%sDespues, vuelve a ejecutar el instalador.%s\n' "$C_AMAR" "$C_RESET"
    if [ "$SIMULAR" -eq 1 ]; then
        simula "se detendria aqui (codigo 1) porque Handy esta abierto"
    else
        exit 1
    fi
else
    ok "Handy no esta en ejecucion"
fi

# =====================================================================
#  Eleccion del modelo del asistente
# =====================================================================

paso "IA del asistente (resumen / redaccion)"
MOTIVO_MODELO=""
MODELOS_ASISTENTE=()
if [ "$SOLO_DICTADO" -eq 1 ]; then
    printf '%s  Modo SOLO DICTADO (--solo-dictado): no se instala IA ni modelos.%s\n' "$C_CYAN" "$C_RESET"
elif [ -n "$ASISTENTE_MODELO" ]; then
    MOTIVO_MODELO="forzado con --modelo"
elif VRAM=$(obtener_vram_nvidia); then
    if [ "$VRAM" -lt "$VRAM_MINIMA" ]; then
        ASISTENTE_MODELO="$MODELO_LIGERO"
        MOTIVO_MODELO="GPU NVIDIA con $VRAM MiB de VRAM (menos de $VRAM_MINIMA MiB)"
    else
        ASISTENTE_MODELO="$MODELO_ESTANDAR"
        MOTIVO_MODELO="GPU NVIDIA con $VRAM MiB de VRAM ($VRAM_MINIMA MiB o mas)"
    fi
else
    # Sin GPU NVIDIA: este PC no puede mover un modelo de IA con soltura.
    # Se instala SOLO dictado (el asistente no es obligatorio para transcribir).
    SOLO_DICTADO=1
    printf '%s  No se detecta GPU NVIDIA: se instala SOLO dictado (sin IA).%s\n' "$C_AMAR" "$C_RESET"
    printf '%s  Para forzar la IA en CPU igualmente, usa --modelo qwen3:4b-instruct.%s\n' "$C_AMAR" "$C_RESET"
fi
if [ "$SOLO_DICTADO" -eq 0 ]; then
    printf '%s  Modelo elegido: %s (%s)%s\n' "$C_CYAN" "$ASISTENTE_MODELO" "$MOTIVO_MODELO" "$C_RESET"
    MODELOS_ASISTENTE=("$ASISTENTE_MODELO")
    [ "$ASISTENTE_MODELO" != "$MODELO_LIGERO" ] && MODELOS_ASISTENTE+=("$MODELO_LIGERO")
fi

# =====================================================================
#  Fase 1: Handy
# =====================================================================

paso "[1/6] Handy (dictado por voz)"
HANDY_EXE=""
if HANDY_EXE=$(handy_ejecutable); then
    HANDY_VER="$(handy_version 2>/dev/null | head -1)"
    VER_TXT="${HANDY_VER:-desconocida}"
    if printf '%s' "$VER_TXT" | grep -qE '^[0-9]'; then
        ok "Handy ya instalado: $VER_TXT  ($HANDY_EXE)"
        if [ "$(printf '%s\n%s\n' "$VER_TXT" "0.9.8" | sort -V | head -1)" != "0.9.8" ]; then
            aviso "Version antigua ($VER_TXT). Se recomienda actualizar a 0.9.8 o superior"
        fi
    else
        ok "Handy ya instalado ($HANDY_EXE)"
    fi
else
    aviso "Handy no esta instalado"
    if [ "$SIMULAR" -eq 1 ]; then
        simula "instalaria Handy (metodo: $METODO): .deb con 'sudo apt install' o AppImage en ~/.local/bin"
    else
        if instalar_handy; then
            ok "Handy instalado ($HANDY_EXE)"
        else
            fallo "Handy no se ha instalado correctamente (revisa los avisos)"
        fi
    fi
fi

# =====================================================================
#  Fase 2: Ollama (instalacion + servidor en marcha)
# =====================================================================

paso "[2/6] Ollama (IA local)"
SERVIDOR_OLLAMA=0
if [ "$SOLO_DICTADO" -eq 1 ]; then
    ok "Omitido: modo solo dictado (no se instala ni arranca Ollama)"
elif command -v ollama >/dev/null 2>&1; then
    ok "Ollama ya instalado ($(command -v ollama))"
else
    aviso "Ollama no esta instalado"
    if [ "$SIMULAR" -eq 1 ]; then
        simula "instalaria Ollama con: curl -fsSL https://ollama.com/install.sh | sh"
    else
        printf '  Instalando Ollama...\n'
        if curl -fsSL https://ollama.com/install.sh | sh; then
            ok "Ollama instalado"
        else
            fallo "Ollama no se ha instalado (se necesitan permisos de administrador)"
        fi
    fi
fi

# Servidor de Ollama escuchando en 127.0.0.1:11434
if [ "$SOLO_DICTADO" -eq 0 ]; then
    if probar_ollama; then
        SERVIDOR_OLLAMA=1
        ok "Servidor de Ollama respondiendo en http://127.0.0.1:11434"
    else
        aviso "El servidor de Ollama no responde"
        if [ "$SIMULAR" -eq 1 ]; then
            simula "arrancaria el servidor (systemctl start ollama o 'ollama serve') y esperaria hasta 60 s"
        else
            arrancar_ollama
            printf '  Esperando a que arranque el servidor (hasta 60 s)...\n'
            i=0
            while [ "$i" -lt 30 ]; do
                sleep 2
                if probar_ollama; then SERVIDOR_OLLAMA=1; break; fi
                i=$((i + 1))
            done
            if [ "$SERVIDOR_OLLAMA" -eq 1 ]; then ok "Servidor de Ollama en marcha"
            else aviso "El servidor de Ollama no arranca: abre Ollama y repite el instalador"; fi
        fi
    fi
fi

# =====================================================================
#  Fase 3: Modelos del asistente
# =====================================================================

paso "[3/6] Modelos del asistente (Ollama)"
MODELOS_PRESENTES=""
if [ "$SOLO_DICTADO" -eq 1 ]; then
    ok "Omitido: modo solo dictado (no se descargan modelos de IA)"
else
    MODELOS_PRESENTES="$(obtener_modelos_ollama 2>/dev/null || true)"
fi
for modelo in "${MODELOS_ASISTENTE[@]}"; do
    if tiene_modelo "$MODELOS_PRESENTES" "$modelo"; then
        ok "Modelo presente: $modelo"
    else
        aviso "Modelo ausente: $modelo"
        if [ "$SIMULAR" -eq 1 ]; then
            simula "descargaria el modelo: ollama pull $modelo"
        else
            printf '  Descargando %s (varios GB, puede tardar)...\n' "$modelo"
            if ollama pull "$modelo"; then
                ok "Modelo descargado: $modelo"
            else
                fallo "No se ha podido descargar $modelo"
            fi
        fi
    fi
done

# =====================================================================
#  Fase 4: Modelo de dictado (Cohere Transcribe 2B)
# =====================================================================

paso "[4/6] Modelo de dictado (Cohere Transcribe 2B, ~1,7 GB)"
descargar_modelo_dictado || true

# =====================================================================
#  Fase 5: Configuracion de Handy
# =====================================================================

paso "[5/6] Configuracion de Handy"

if handy_en_ejecucion; then
    printf '  %sHandy esta en ejecucion.%s\n' "$C_ROJO" "$C_RESET"
    printf '  %sCierra Handy (bandeja -> Salir) y vuelve a ejecutar el instalador.%s\n' "$C_AMAR" "$C_RESET"
    if [ "$SIMULAR" -eq 1 ]; then
        simula "no se tocaria la configuracion (se detendria con codigo 1)"
    else
        exit 1
    fi
fi

CFG="$(handy_cfg_file)"
CFG_DIR="$(handy_cfg_dir)"
MERGE_OK=0
CAMINO=""

if [ -f "$CFG" ]; then
    CAMINO="merge"
    printf '  %sCamino: MERGE (habia configuracion previa: se conserva tu microfono, atajos y prompts)%s\n' "$C_CYAN" "$C_RESET"
else
    CAMINO="copia"
    printf '  %sCamino: COPIA completa de config/handy-settings.json (no habia configuracion previa)%s\n' "$C_CYAN" "$C_RESET"
fi
if [ "$SOLO_DICTADO" -eq 1 ]; then
    printf '  %sSolo dictado: se desactivara el post-procesado IA (post_process_enabled=false)%s\n' "$C_CYAN" "$C_RESET"
elif [ "$ASISTENTE_MODELO" != "$MODELO_ESTANDAR" ]; then
    printf '  %sPC ligero: se ajustara post_process_models.custom a %s%s\n' "$C_CYAN" "$ASISTENTE_MODELO" "$C_RESET"
fi

if [ "$SIMULAR" -eq 1 ]; then
    if [ "$CAMINO" = "merge" ]; then
        simula "hararia copia de settings_store.json a settings_store.json.bak y mergearia selected_model, custom_words, extra_recording_buffer_ms y keyboard_implementation"
    else
        simula "crearia $CFG copiando config/handy-settings.json"
    fi
    if [ "$SOLO_DICTADO" -eq 1 ]; then
        simula "desactivaria post_process_enabled (solo dictado)"
    elif [ "$ASISTENTE_MODELO" != "$MODELO_ESTANDAR" ]; then
        simula "ajustaria post_process_models.custom a $ASISTENTE_MODELO"
    fi
else
    mkdir -p "$CFG_DIR"
    ARGS=(merge --repo "$REPO_CONFIG" --live "$CFG")
    [ "$SOLO_DICTADO" -eq 0 ] && [ "$ASISTENTE_MODELO" != "$MODELO_ESTANDAR" ] && ARGS+=(--assistant-model "$ASISTENTE_MODELO")
    [ "$SOLO_DICTADO" -eq 1 ] && ARGS+=(--solo-dictado)
    [ "$CAMINO" = "copia" ] && ARGS+=(--full-copy)
    if python3 "$SCRIPT_DIR/handy-config.py" "${ARGS[@]}"; then
        MERGE_OK=1
        ok "Configuracion aplicada en $CFG"
    else
        fallo "No se ha podido aplicar la configuracion de Handy"
    fi
fi

# =====================================================================
#  Fase 6: Lector de voz (Kokoro)
# =====================================================================

paso "[6/6] Lector de voz (Kokoro, ~0,7 GB entre modelo y entorno Python)"

LECTOR_PY="$LECTOR_DIR/.venv/bin/python"
LECTOR_DESKTOP="$HOME/.config/autostart/lector-voz.desktop"

if [ "$SIN_LECTOR" -eq 1 ]; then
    ok "Omitido: --sin-lector (no se instala el lector de voz)"
elif [ "$SIMULAR" -eq 1 ]; then
    simula "pararia el lector si esta en marcha y copiaria lector/*.py y requirements.txt a $LECTOR_DIR"
    simula "copiaria config/lector.json solo si no existe ya en $LECTOR_DIR"
    if UV_SIM=$(buscar_uv); then ok "uv disponible ($UV_SIM)"
    else simula "instalaria uv: curl -LsSf https://astral.sh/uv/install.sh | sh"; fi
    if [ -x "$LECTOR_PY" ]; then ok "Entorno Python 3.12 ya creado"
    else simula "crearia el entorno: uv venv -p 3.12 $LECTOR_DIR/.venv"; fi
    simula "instalaria las dependencias: uv pip install -p <python del entorno> -r requirements.txt"
    for entrada in "${LECTOR_ARCHIVOS[@]}"; do
        IFS=: read -r lnom lbytes lsha <<< "$entrada"
        if verificar_archivo "$LECTOR_DIR/modelo/$lnom" "$lbytes" "$lsha"; then
            ok "$lnom ya presente y verificado (sha256 y tamano)"
        else
            simula "descargaria $lnom ($lbytes bytes) de github.com; verifica sha256 y tamano"
        fi
    done
    simula "crearia el autoarranque: $LECTOR_DESKTOP"
    simula "arrancaria el lector en segundo plano"
else
    # 2. Parar el lector si esta en marcha
    if lector_en_marcha; then
        pkill -f "$LECTOR_DIR/lector.py" 2>/dev/null
        sleep 1
        ok "Lector en marcha parado (se reiniciara al terminar)"
    fi

    # 3. Copiar archivos (la config solo si no existe: se conservan los cambios del usuario)
    LECTOR_COPIA_OK=0
    if mkdir -p "$LECTOR_DIR/modelo" \
        && cp -f "$REPO_ROOT"/lector/*.py "$REPO_ROOT/lector/requirements.txt" "$LECTOR_DIR/"; then
        LECTOR_COPIA_OK=1
        if [ ! -f "$LECTOR_DIR/lector.json" ]; then
            cp "$REPO_ROOT/config/lector.json" "$LECTOR_DIR/lector.json" && ok "Config del lector creada (lector.json)"
        else
            ok "Config del lector conservada (ya existia lector.json)"
        fi
        ok "Archivos del lector copiados a $LECTOR_DIR"
    else
        fallo "No se han podido copiar los archivos del lector a $LECTOR_DIR"
    fi

    # 4. uv + entorno Python 3.12 (kokoro-onnx exige Python < 3.14)
    LECTOR_VENV_OK=0
    if [ "$LECTOR_COPIA_OK" -eq 1 ]; then
        UV=""
        if ! UV=$(buscar_uv); then
            printf '  Instalando uv...\n'
            curl -LsSf https://astral.sh/uv/install.sh | sh
            UV=$(buscar_uv) || UV=""
        fi
        if [ -z "$UV" ]; then
            fallo "No se encuentra uv (instalalo con: curl -LsSf https://astral.sh/uv/install.sh | sh) y repite el instalador"
        else
            ok "uv disponible ($UV)"
            if [ ! -x "$LECTOR_PY" ]; then
                printf '  Creando el entorno Python 3.12 (puede descargar Python)...\n'
                "$UV" venv -p 3.12 "$LECTOR_DIR/.venv"
            fi
            if [ -x "$LECTOR_PY" ]; then
                printf '  Instalando dependencias del lector...\n'
                if "$UV" pip install -p "$LECTOR_PY" -r "$LECTOR_DIR/requirements.txt"; then
                    ok "Entorno Python del lector listo"
                    LECTOR_VENV_OK=1
                else
                    fallo "No se han podido instalar las dependencias del lector"
                fi
            else
                fallo "No se ha podido crear el entorno Python 3.12 del lector"
            fi
        fi
    fi

    # 5. Modelo (2 archivos) con sha256 y tamano
    LECTOR_MODELO_OK=0
    if [ "$LECTOR_COPIA_OK" -eq 1 ]; then
        LECTOR_MODELO_OK=1
        for entrada in "${LECTOR_ARCHIVOS[@]}"; do
            IFS=: read -r lnom lbytes lsha <<< "$entrada"
            destino="$LECTOR_DIR/modelo/$lnom"
            if verificar_archivo "$destino" "$lbytes" "$lsha"; then
                ok "$lnom ya presente y verificado (sha256 y tamano)"
                continue
            fi
            if [ -f "$destino" ]; then
                aviso "$lnom no coincide (sha256 o tamano): se descarga de nuevo"
                rm -f "$destino"
            fi
            printf '  Descargando %s...\n' "$lnom"
            if curl -L --fail --retry 3 -o "$destino" "$LECTOR_URL_BASE/$lnom" && verificar_archivo "$destino" "$lbytes" "$lsha"; then
                ok "$lnom descargado y verificado"
            else
                rm -f "$destino"
                fallo "No se ha podido descargar $lnom (repite el instalador con conexion)"
                LECTOR_MODELO_OK=0
            fi
        done
    fi

    # 6. Autoarranque
    LECTOR_AUTO_OK=0
    if [ "$LECTOR_VENV_OK" -eq 1 ]; then
        if mkdir -p "$HOME/.config/autostart" && cat > "$LECTOR_DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Lector de voz
Comment=Lector de voz local (Kokoro)
Exec=$LECTOR_PY $LECTOR_DIR/lector.py
Path=$LECTOR_DIR
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
        then
            LECTOR_AUTO_OK=1
            ok "Autoarranque creado ($LECTOR_DESKTOP)"
        else
            fallo "No se ha podido crear el autoarranque del lector"
        fi
    fi

    # 8. Dependencias del sistema (aviso, no bloquea)
    if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
        aviso "Falta libportaudio2 (el lector no podra sonar). Instalala con: sudo apt install libportaudio2"
    fi
    if ! command -v xclip >/dev/null 2>&1 && ! command -v xsel >/dev/null 2>&1 && ! command -v wl-paste >/dev/null 2>&1; then
        aviso "Falta xclip, xsel o wl-paste (el lector no podra leer el portapapeles). Instala uno con: sudo apt install xclip"
    fi
    if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
        aviso "Sesion Wayland: los atajos globales del lector solo funcionan en X11. Entra con una sesion Xorg (o asigna un atajo del sistema que ejecute: $LECTOR_PY $LECTOR_DIR/lector.py --probar)"
    fi

    # 7. Arrancarlo en segundo plano
    if [ "$LECTOR_AUTO_OK" -eq 1 ] && [ "$LECTOR_MODELO_OK" -eq 1 ]; then
        nohup setsid "$LECTOR_PY" "$LECTOR_DIR/lector.py" >/dev/null 2>&1 &
        sleep 6
        if lector_en_marcha; then
            ok "Lector en marcha (atajo Ctrl+Alt+R)"
        else
            aviso "El lector no parece estar en marcha: mira $LECTOR_DIR/lector.log"
        fi
    fi
fi

# =====================================================================
#  Verificacion y resumen final
# =====================================================================

printf '\n%s========================= RESUMEN =========================%s\n' "$C_CYAN" "$C_RESET"
[ "$SIMULAR" -eq 1 ] && printf '%s (simulacion: este es el estado actual y lo que haria)%s\n' "$C_CYAN" "$C_RESET"

# Handy
if HANDY_EXE=$(handy_ejecutable); then
    VER_FIN="$(handy_version 2>/dev/null | head -1)"
    if [ -n "$VER_FIN" ]; then
        dato "Handy" "$VER_FIN  ($HANDY_EXE)"
    else
        dato "Handy" "instalado  ($HANDY_EXE)"
    fi
else
    dato "Handy" "no instalado"
fi

# Modelo de dictado + refs/main
GGUF="$(gguf_file)"; REFS_MAIN="$(refs_main_file)"
if verificar_gguf "$GGUF"; then
    dato "Modelo de dictado" "Cohere Q5_K_M presente ($GGUF_BYTES bytes, sha256 correcto)"
elif [ -f "$GGUF" ]; then
    dato "Modelo de dictado" "presente pero NO coincide"
else
    dato "Modelo de dictado" "no descargado"
fi
if [ -f "$REFS_MAIN" ]; then
    dato "refs/main" "$(tr -d '\r\n' < "$REFS_MAIN")"
else
    dato "refs/main" "no existe"
fi

# Ollama / IA
if [ "$SOLO_DICTADO" -eq 1 ]; then
    dato "IA / Ollama" "solo dictado (no requerido)"
elif probar_ollama; then
    dato "Ollama" "servidor en marcha (http://127.0.0.1:11434)"
    MODELOS_FIN="$(obtener_modelos_ollama 2>/dev/null || true)"
    for modelo in "${MODELOS_ASISTENTE[@]}"; do
        if tiene_modelo "$MODELOS_FIN" "$modelo"; then dato "Modelo $modelo" "presente"
        else dato "Modelo $modelo" "AUSENTE"; fi
    done
else
    dato "Ollama" "instalado pero el servidor no responde"
fi

# Configuracion
if [ "$SIMULAR" -eq 1 ]; then
    dato "Settings" "sin tocar ($CFG)"
elif [ "$MERGE_OK" -eq 1 ]; then
    dato "Settings" "aplicado en $CFG"
    dato "Camino" "$CAMINO"
else
    dato "Settings" "NO aplicado"
fi

# Lector de voz
if [ "$SIN_LECTOR" -eq 1 ]; then
    dato "Lector de voz" "omitido (--sin-lector)"
else
    LECTOR_MODELO_FIN="no"
    LECTOR_ARCHIVOS_OK=1
    for entrada in "${LECTOR_ARCHIVOS[@]}"; do
        IFS=: read -r lnom lbytes lsha <<< "$entrada"
        verificar_archivo "$LECTOR_DIR/modelo/$lnom" "$lbytes" "$lsha" || LECTOR_ARCHIVOS_OK=0
    done
    [ "$LECTOR_ARCHIVOS_OK" -eq 1 ] && LECTOR_MODELO_FIN="si"
    LECTOR_AUTO_FIN="no"
    [ -f "$HOME/.config/autostart/lector-voz.desktop" ] && LECTOR_AUTO_FIN="si"
    dato "Lector de voz" "modelo verificado: $LECTOR_MODELO_FIN | autoarranque: $LECTOR_AUTO_FIN"
fi

dato "Fallos" "$FALLOS"
dato "Avisos" "$AVISOS"

printf '\n%sSiguientes pasos:%s\n' "$C_CYAN" "$C_RESET"
printf ' 1. Abre Handy y elige tu microfono en Ajustes.\n'
printf ' 2. Prueba los tres atajos: Ctrl+Alt+Espacio (dictado), Ctrl+Shift+Espacio (asistente) y Ctrl+Alt+R (lee el portapapeles en voz alta).\n'
printf ' 3. Para cambiar de modelo de dictado: Handy -> Ajustes -> Modelos.\n'
printf ' 4. El resto (modelo del asistente, prompts, diccionario): seccion Configuracion del README.\n'

# Abrir Handy al terminar (salvo --simular o --no-abrir)
if [ "$SIMULAR" -eq 0 ] && [ "$NO_ABRIR" -eq 0 ]; then
    printf '\n%sPulsa INTRO para abrir Handy ahora (o Ctrl+C para terminar).%s\n' "$C_VERDE" "$C_RESET"
    read -r _ || true
    if HANDY_EXE=$(handy_ejecutable); then
        setsid "$HANDY_EXE" >/dev/null 2>&1 &
    else
        printf 'No se ha encontrado el ejecutable de Handy para abrirlo.\n'
    fi
fi

printf '\n'
if [ "$FALLOS" -gt 0 ]; then
    printf '%sTerminado con %s fallo(s). Revisa los mensajes de arriba.%s\n' "$C_ROJO" "$FALLOS" "$C_RESET"
    exit 1
fi
if [ "$SIMULAR" -eq 1 ]; then
    printf '%sSimulacion terminada. No se ha modificado nada.%s\n' "$C_CYAN" "$C_RESET"
else
    printf '%sInstalacion terminada.%s\n' "$C_VERDE" "$C_RESET"
fi
exit 0
