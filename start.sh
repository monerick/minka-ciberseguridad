#!/bin/bash
# start.sh — Inicia MINKA VOZ

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/home/joziel/minka_voz"

if [ ! -f "$APP_DIR/minka_voz.py" ]; then
    echo "Error: No se encontró minka_voz.py"
    exit 1
fi

cd "$APP_DIR"

echo "╔══════════════════════════════════════════╗"
echo "║   🌿 MINKA VOZ                         ║"
echo "║   [1] Estudiante / Padre                ║"
echo "║   [2] Profesor / Administrador          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
read -p "  › " choice

case $choice in
    1) python3 minka_voz.py ;;
    2) python3 profesor_dashboard.py ;;
    *) echo "Opción inválida" ;;
esac
