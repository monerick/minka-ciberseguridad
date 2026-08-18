#!/bin/bash
# start.sh — Inicia MINKA VOZ desde la raíz del proyecto

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/home/joziel/minka_voz"

if [ ! -f "$APP_DIR/minka_voz.py" ]; then
    echo "Error: No se encontró minka_voz.py"
    exit 1
fi

cd "$APP_DIR"
python3 minka_voz.py
