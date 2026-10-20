#!/usr/bin/env bash
# Instalador en 1 clic - Asistente de voz local (Handy + Ollama) para Linux
#
# Doble clic o: ./Instalar.sh
# Opciones extra: pasa los mismos argumentos que install.sh (--simular, --modelo, --no-abrir, --metodo, --sin-lector).

set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS1="$DIR/scripts/install.sh"

if [ ! -f "$PS1" ]; then
    echo "ERROR: no se encuentra \"$PS1\""
    echo "Copia la carpeta completa del repositorio y vuelve a intentarlo."
    exit 1
fi

exec bash "$PS1" "$@"
