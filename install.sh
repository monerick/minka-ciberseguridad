#!/bin/bash
# install.sh — Instala dependencias de MINKA VOZ

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/home/joziel/minka_voz"

echo "╔══════════════════════════════════════════╗"
echo "║   🌿 Instalando MINKA VOZ               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

PYTHON=$(which python3 || which python)
echo "Python: $PYTHON"
echo ""

# Dependencias rápidas
echo "1/2 Instalando dependencias principales..."
$PYTHON -m pip install sounddevice soundfile gTTS pygame pynput bcrypt cryptography anthropic numpy

echo ""
echo "2/2 Instalando whisper (puede tardar ~5 min)..."
$PYTHON -m pip install openai-whisper

# Directorio seguro
mkdir -p "$HOME/.minka_secure"
chmod 700 "$HOME/.minka_secure"

echo ""
echo "✓ Instalación completada"
echo "Ejecuta: ./start.sh"
