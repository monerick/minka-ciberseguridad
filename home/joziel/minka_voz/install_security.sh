#!/bin/bash
# install_security.sh — Instala dependencias de seguridad para MINKA VOZ

echo "╔══════════════════════════════════════════╗"
echo "║   🔒 Instalando seguridad MINKA VOZ    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Detectar Python
PYTHON=$(which python3 || which python)
if [ -z "$PYTHON" ]; then
    echo "Error: Python no encontrado"
    exit 1
fi

echo "Usando Python: $PYTHON"
echo ""

# Instalar dependencias de seguridad
echo "Instalando dependencias de seguridad..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install bcrypt cryptography

# Crear directorio oculto
HIDDEN_DIR="$HOME/.minka_secure"
echo ""
echo "Creando directorio seguro: $HIDDEN_DIR"
mkdir -p "$HIDDEN_DIR"
chmod 700 "$HIDDEN_DIR"

echo ""
echo "✓ Dependencias instaladas correctamente"
echo ""
echo "Crea tu primera cuenta ejecutando:"
echo "  $PYTHON minka_voz.py"
