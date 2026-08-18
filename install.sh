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
echo "Instalando dependencias..."
$PYTHON -m pip install sounddevice soundfile gTTS pygame pynput bcrypt cryptography anthropic numpy SpeechRecognition

# Directorio seguro
mkdir -p "$HOME/.minka_secure"
chmod 700 "$HOME/.minka_secure"

echo ""
echo "✓ Instalación completada"
echo "Ejecuta: ./start.sh"
