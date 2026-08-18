#!/bin/bash
# install.sh — Instala todo desde la raíz del proyecto

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/home/joziel/minka_voz"

if [ ! -f "$APP_DIR/install_security.sh" ]; then
    echo "Error: No se encontró install_security.sh"
    exit 1
fi

cd "$APP_DIR"
./install_security.sh
