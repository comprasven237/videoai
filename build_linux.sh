#!/bin/bash
# VIDEOAI - Script de construcción para Linux (AppImage)

set -e

APP_NAME="VIDEOAI"
VERSION="1.0.0"
ARCH=$(uname -m)

echo "🎬 Construyendo $APP_NAME v$VERSION para Linux ($ARCH)"
echo "=================================================="

# Crear directorios
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/lib
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# Copiar archivos principales
echo "📦 Copiando archivos..."
cp launcher.py main.py config.py pipeline.py requirements.txt config.yaml .env.example AppDir/usr/bin/
cp README.md INSTALL.md AppDir/
cp -r templates static prompts helpers AppDir/usr/bin/

# Crear desktop file
echo "🖼️  Creando desktop file..."
cat > AppDir/VIDEOAI.desktop << EOF
[Desktop Entry]
Type=Application
Name=VIDEOAI
Comment=Producción de Vídeo Automatizada con IA
Exec=launcher.py
Icon=videoai
Categories=AudioVideo;Graphics;
Keywords=video;ai;edit;
EOF

# Copiar desktop file a ubicación estándar
cp AppDir/VIDEOAI.desktop AppDir/usr/share/applications/

# Crear ícono placeholder (si no existe)
if [ ! -f "assets/icon.png" ]; then
    echo "🎨 Creando ícono placeholder..."
    # Crear un PNG simple de 256x256
    python3 -c "
from PIL import Image, ImageDraw
img = Image.new('RGB', (256, 256), color='#0f0f0f')
d = ImageDraw.Draw(img)
d.rectangle([50, 50, 206, 206], fill='#00d4aa')
d.text((80, 120), 'VIDEOAI', fill='#000000')
img.save('assets/icon.png')
" 2>/dev/null || echo "⚠️  Pillow no disponible, usando ícono genérico"
fi

# Copiar ícono
if [ -f "assets/icon.png" ]; then
    cp assets/icon.png AppDir/videoai.png
    cp assets/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/videoai.png
fi

# Descargar linuxdeploy si no existe
if [ ! -f "linuxdeploy-x86_64.AppImage" ]; then
    echo "📥 Descargando linuxdeploy..."
    wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
    chmod +x linuxdeploy-x86_64.AppImage
fi

# Construir AppImage
echo "🔨 Construyendo AppImage..."
./linuxdeploy-x86_64.AppImage \
    --appdir AppDir \
    -d AppDir/VIDEOAI.desktop \
    -i AppDir/videoai.png \
    --output appimage

# Mover resultado
if [ -f "${APP_NAME}-${VERSION}-${ARCH}.AppImage" ]; then
    mv "${APP_NAME}-${VERSION}-${ARCH}.AppImage" dist/
    echo "✅ AppImage creado: dist/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
else
    # Buscar cualquier AppImage generado
    find . -name "*.AppImage" -exec mv {} dist/ \; 2>/dev/null || true
    echo "✅ AppImage(s) movido(s) a dist/"
fi

echo ""
echo "🎉 ¡Construcción completada!"
echo "=========================================="
echo "Para ejecutar:"
echo "  ./dist/${APP_NAME}-*.AppImage"
echo ""
echo "O instalar en el sistema:"
echo "  sudo mv dist/${APP_NAME}-*.AppImage /opt/${APP_NAME}.AppImage"
echo "  sudo ln -s /opt/${APP_NAME}.AppImage /usr/local/bin/${APP_NAME,,}"
