# 🚀 VIDEOAI - Guía Rápida de Inicio

## ⚡ Inicio Rápido (30 segundos)

### 1. Descargar
- Ve a [GitHub Releases](https://github.com/tu-usuario/videoai/releases)
- Descarga la versión para tu sistema:
  - **Windows**: `VIDEOAI-Windows.exe` o `VIDEOAI-Installer.exe`
  - **macOS**: `VIDEOAI-macOS.zip` (contiene VIDEOAI.app)
  - **Linux**: `VIDEOAI-Linux.AppImage`

### 2. Instalar/Ejecutar

**Windows:**
```
Opción A: Ejecutar VIDEOAI-Installer.exe (recomendado)
Opción B: Doble-click en VIDEOAI-Windows.exe
```

**macOS:**
```
1. Extraer VIDEOAI-macOS.zip
2. Arrastrar VIDEOAI.app a Aplicaciones
3. Abrir desde Aplicaciones
```

**Linux:**
```bash
chmod +x VIDEOAI-Linux.AppImage
./VIDEOAI-Linux.AppImage
```

### 3. Configurar IA (Primer Uso)
El wizard te guiará para configurar:
- Tu servidor LLM local O API externa
- Duración objetivo del clip (30-90 segundos)
- Carpeta de entrada de vídeos

### 4. ¡Comenzar!
- Sube vídeos con drag & drop
- Pega URLs de YouTube/TikTok/Instagram
- Click en "🚀 INICIAR PROCESO"

---

## 📁 Estructura del Proyecto

```
videoai/
├── launcher.py           ← Botón de inicio GUI/CLI
├── main.py               ← Servidor FastAPI + Dashboard
├── pipeline.py           ← Orquestador de 11 etapas
├── config.py             ← Configuración centralizada
├── requirements.txt      ← Dependencias Python
├── config.yaml           ← Valores por defecto
├── .env.example          ← Plantilla de configuración
│
├── helpers/              ← Módulos auxiliares
│   ├── llm_client.py     ← Cliente HTTP agnóstico
│   ├── stt_engine.py     ← Transcripción local
│   ├── timestamp_aligner.py
│   ├── video_processor.py
│   ├── animation_executor.py
│   ├── file_watcher.py
│   └── uploader.py
│
├── templates/            ← HTML del Dashboard
│   ├── index.html
│   └── setup_wizard.html
│
├── static/               ← CSS y JavaScript
│   ├── style.css
│   └── app.js
│
├── prompts/              ← Prompts para IA
│   ├── highlight_extraction.md
│   ├── script_cleanup.md
│   ├── animation_plan.md
│   ├── thumbnail_title.md
│   └── metadata_gen.md
│
├── cleaning/raw/         ← Vídeos de entrada
├── output/               ← Clips finales
├── logs/                 ← Logs del sistema
└── state/                ← Estado del pipeline
```

---

## 🔧 Scripts de Construcción

### Windows
```batch
build_windows.bat    # Crea VIDEOAI.exe con PyInstaller
```

### macOS
```bash
build_macos.sh       # Crea VIDEOAI.app con py2app
setup_macos.py       # Configuración para py2app
```

### Linux
```bash
build_linux.sh       # Crea VIDEOAI.AppImage
```

### Instalador Windows (Opcional)
```
installer.iss        # Script para Inno Setup
```

---

## 🎯 Comandos Útiles

### Desarrollo
```bash
# Activar entorno virtual
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar con launcher GUI
python launcher.py

# Ejecutar directamente
python main.py

# Ver logs en tiempo real
tail -f logs/*.log
```

### Construcción
```bash
# Windows
build_windows.bat

# macOS
./build_macos.sh

# Linux
./build_linux.sh
```

---

## ❓ Problemas Comunes

### "Puerto 5555 ya en uso"
```bash
# Windows
netstat -ano | findstr :5555
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5555
kill -9 <PID>
```

### "FFmpeg no encontrado"
- Windows: Instalar desde https://ffmpeg.org y agregar al PATH
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### "No module named 'xxx'"
```bash
pip install -r requirements.txt --upgrade
```

---

## 📞 Soporte

- **Documentación completa**: Ver `README.md`
- **Guía de instalación**: Ver `INSTALL.md`
- **Reportar bugs**: GitHub Issues
- **Discord**: [link a comunidad]

---

**VIDEOAI** - Transforma tus vídeos largos en clips virales automáticamente 🎬✨
