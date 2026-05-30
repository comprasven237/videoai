#!/bin/bash
# VIDEOAI - Script de construcción para macOS (.app)

set -e

APP_NAME="VIDEOAI"
VERSION="1.0.0"

echo "🎬 Construyendo $APP_NAME v$VERSION para macOS"
echo "=================================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado"
    echo "Instala Python desde https://python.org o usa 'brew install python'"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔌 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📥 Instalando dependencias..."
pip install -r requirements.txt --quiet
pip install py2app --quiet

# Limpiar construcciones anteriores
echo "🧹 Limpiando..."
rm -rf build dist *.egg-info

# Construir aplicación
echo "🔨 Construyendo aplicación macOS..."
python3 setup_macos.py py2app

# Verificar resultado
if [ -d "dist/${APP_NAME}.app" ]; then
    echo ""
    echo "✅ ¡Construcción completada!"
    echo "=========================================="
    echo "Aplicación creada: dist/${APP_NAME}.app"
    echo ""
    echo "Para ejecutar:"
    echo "  open dist/${APP_NAME}.app"
    echo ""
    echo "Para distribuir:"
    echo "  1. Comprimir en ZIP: zip -r ${APP_NAME}.zip dist/${APP_NAME}.app"
    echo "  2. O crear DMG con create-dmg (requiere instalación adicional)"
    echo ""
    
    # Mostrar información de la app
    echo "📊 Información de la aplicación:"
    ls -lh dist/${APP_NAME}.app
else
    echo "❌ Error: No se pudo crear la aplicación .app"
    echo "Revisa los mensajes de error arriba"
    exit 1
fi

# Desactivar entorno virtual
deactivate
