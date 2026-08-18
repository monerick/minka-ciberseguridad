#!/bin/bash
# install.sh — Instala TODAS las dependencias de MINKA VOZ

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/home/joziel/minka_voz"

echo "╔══════════════════════════════════════════╗"
echo "║   🌿 Instalando MINKA VOZ completo     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

PYTHON=$(which python3 || which python)
echo "Usando Python: $PYTHON"
echo ""

# Instalar Todas las dependencias
echo "Instalando dependencias..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install openai-whisper sounddevice soundfile anthropic gTTS pygame numpy pynput bcrypt cryptography

# Crear directorio seguro
HIDDEN_DIR="$HOME/.minka_secure"
echo ""
echo "Creando directorio seguro: $HIDDEN_DIR"
mkdir -p "$HIDDEN_DIR"
chmod 700 "$HIDDEN_DIR"

echo ""
echo "✓ Todo instalado correctamente"
echo ""
echo "Ejecuta: ./start.sh"
