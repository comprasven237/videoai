# 🎬 VIDEOAI - Instalador y Empaquetado

Guías de instalación para Windows, macOS y Linux.

---

## 📦 Opción 1: Instalación Manual (Recomendada para Desarrollo)

### Requisitos Previos

- **Python 3.9+** instalado
- **FFmpeg** instalado y en PATH
- **Git** (opcional, para clonar el repositorio)

### Pasos de Instalación

#### 1. Descargar/Clonar el Proyecto

```bash
# Opción A: Clonar desde GitHub
git clone https://github.com/tu-usuario/videoai.git
cd videoai

# Opción B: Descargar ZIP desde GitHub y extraer
```

#### 2. Crear Entorno Virtual

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

#### 4. Instalar FFmpeg

**Windows:**
- Descargar desde: https://ffmpeg.org/download.html
- Extraer y agregar `bin` al PATH del sistema

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

#### 5. Ejecutar la Aplicación

**Opción A: Con Launcher GUI (recomendado)**
```bash
python launcher.py
```

**Opción B: Directo con main.py**
```bash
python main.py
```

**Opción C: En segundo plano**
```bash
# Windows
start python main.py

# macOS/Linux
python main.py &
```

---

## 🍎 Opción 2: Aplicación Nativa macOS (.app)

### Requisitos
- macOS 10.13+
- Python 3.9+
- py2app: `pip install py2app`

### Crear App Bundle

1. **Crear setup.py para macOS:**

```python
from setuptools import setup
import sys

APP = ['launcher.py']
DATA_FILES = [
    'main.py',
    'config.py',
    'pipeline.py',
    'requirements.txt',
    'config.yaml',
    '.env.example',
    ('templates', ['templates/index.html', 'templates/setup_wizard.html']),
    ('static', ['static/style.css', 'static/app.js']),
    ('prompts', ['prompts/highlight_extraction.md', 'prompts/script_cleanup.md', 
                 'prompts/animation_plan.md', 'prompts/thumbnail_title.md', 
                 'prompts/metadata_gen.md']),
    ('helpers', ['helpers/__init__.py', 'helpers/llm_client.py', 
                 'helpers/stt_engine.py', 'helpers/timestamp_aligner.py',
                 'helpers/video_processor.py', 'helpers/animation_executor.py',
                 'helpers/file_watcher.py', 'helpers/uploader.py']),
]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'assets/icon.icns',  # Opcional: crear ícono
    'packages': ['fastapi', 'uvicorn', 'jinja2', 'requests', 
                 'faster_whisper', 'opencv_python', 'PIL'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

2. **Construir la aplicación:**

```bash
python setup.py py2app
```

3. **La app se creará en:** `dist/VIDEOAI.app`

4. **Distribuir:** Comprimir en ZIP o crear DMG

---

## 🪟 Opción 3: Ejecutable Windows (.exe)

### Requisitos
- Windows 10+
- Python 3.9+
- PyInstaller: `pip install pyinstaller`

### Crear Executable Único

1. **Crear spec file:**

```bash
pyi-makespec --onefile --windowed --name VIDEOAI launcher.py
```

2. **Editar VIDEOAI.spec** para incluir archivos:

```python
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['launcher.py'],
    datas=[
        ('main.py', '.'),
        ('config.py', '.'),
        ('pipeline.py', '.'),
        ('requirements.txt', '.'),
        ('config.yaml', '.'),
        ('.env.example', '.'),
        ('templates', 'templates'),
        ('static', 'static'),
        ('prompts', 'prompts'),
        ('helpers', 'helpers'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'jinja2',
        'requests',
        'faster_whisper',
        'cv2',
        'PIL',
        'numpy',
        'scipy',
    ] + collect_submodules('faster_whisper'),
    ...
)
```

3. **Construir executable:**

```bash
pyinstaller VIDEOAI.spec
```

4. **El executable estará en:** `dist/VIDEOAI.exe`

### Crear Instalador con Inno Setup (Opcional)

1. Descargar Inno Setup: https://jrsoftware.org/isdl.php

2. Crear script `installer.iss`:

```iss
[Setup]
AppName=VIDEOAI
AppVersion=1.0
DefaultDirName={pf}\VIDEOAI
OutputDir=installer_output

[Files]
Source: "dist\VIDEOAI.exe"; DestDir: "{app}"
Source: "main.py"; DestDir: "{app}"
Source: "config.py"; DestDir: "{app}"
; ... agregar todos los archivos necesarios

[Icons]
Name: "{group}\VIDEOAI"; Filename: "{app}\VIDEOAI.exe"
```

3. Compilar instalador desde Inno Setup IDE

---

## 🐧 Opción 4: Linux (AppImage / Flatpak)

### AppImage

1. **Instalar linuxdeploy:**
```bash
wget https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
chmod +x linuxdeploy-x86_64.AppImage
```

2. **Crear AppDir:**
```bash
mkdir -p AppDir/usr/bin
cp launcher.py main.py config.py pipeline.py requirements.txt config.yaml .env.example AppDir/
cp -r templates static prompts helpers AppDir/
```

3. **Crear desktop file** `AppDir/VIDEOAI.desktop`:
```desktop
[Desktop Entry]
Type=Application
Name=VIDEOAI
Exec=launcher.py
Icon=videoai
Categories=AudioVideo;Graphics;
```

4. **Construir AppImage:**
```bash
./linuxdeploy-x86_64.AppImage --appdir AppDir -d VIDEOAI.desktop
```

### Flatpak

Crear `videoai.yml`:
```yaml
app-id: com.videoai.app
runtime: org.freedesktop.Platform
runtime-version: '22.08'
sdk: org.freedesktop.Sdk
command: launcher.py
modules:
  - name: videoai
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app -r requirements.txt
      - install -D launcher.py /app/bin/launcher.py
      - install -D main.py /app/share/videoai/main.py
      # ... instalar todos los archivos
```

---

## 🚀 Uso Después de Instalar

### Primer Uso

1. **Ejecutar la aplicación:**
   - Windows: Doble-click en `VIDEOAI.exe` o `launcher.py`
   - macOS: Abrir `VIDEOAI.app` desde Applications
   - Linux: Ejecutar `./VIDEOAI.AppImage` o `python launcher.py`

2. **Configurar IA:**
   - El wizard de configuración aparecerá automáticamente
   - Configurar endpoint LLM local o API externa
   - Establecer duración objetivo del clip
   - Seleccionar carpeta de entrada de vídeos

3. **Comenzar a producir:**
   - Subir vídeos mediante drag & drop
   - Pegar URLs de YouTube, TikTok, Instagram, etc.
   - Click en "🚀 INICIAR PROCESO"

### Comandos Útiles

```bash
# Ver logs en tiempo real
tail -f logs/*.log

# Reiniciar servidor
python launcher.py

# Actualizar dependencias
pip install -r requirements.txt --upgrade

# Limpiar caché
rm -rf __pycache__ */__pycache__
```

---

## 🔧 Solución de Problemas

### Error: "No module named 'xxx'"
```bash
pip install -r requirements.txt
```

### Error: "FFmpeg not found"
- Verificar que FFmpeg esté instalado y en PATH
- Windows: `set PATH=%PATH%;C:\ffmpeg\bin`
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Error: "Port 5555 already in use"
```bash
# Windows
netstat -ano | findstr :5555
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5555
kill -9 <PID>
```

### Error: "CUDA not available" (para faster-whisper)
- Instalar drivers NVIDIA actualizados
- Reinstalar torch con soporte CUDA:
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📞 Soporte

- Documentación completa: Ver `README.md`
- Reportar bugs: GitHub Issues
- Discord: [link a comunidad]

---

**VIDEOAI** - Transforma tus vídeos largos en clips virales automáticamente 🎬✨
