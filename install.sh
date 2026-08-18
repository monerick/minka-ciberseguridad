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

# Instalar dependencias del sistema (Fedora)
echo "Instalando dependencias del sistema..."
if command -v dnf &> /dev/null; then
    sudo dnf install -y gcc python3-devel portaudio-devel \
        SDL2-devel SDL2_image-devel SDL2_mixer-devel SDL2_ttf-devel \
        freetype-devel libfreetype.so.6 pkg-config
elif command -v apt &> /dev/null; then
    sudo apt install -y gcc python3-dev libportaudio2 portaudio19-dev \
        libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
        libfreetype6-dev pkg-config
fi

# Instalar Todas las dependencias Python
echo ""
echo "Instalando dependencias Python..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install --only-binary :all: openai-whisper sounddevice soundfile gTTS pygame numpy pynput bcrypt cryptography
$PYTHON -m pip install anthropic

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
