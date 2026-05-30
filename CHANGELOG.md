# Changelog

Todos los cambios notables a este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-30

### 🎉 Lanzamiento Inicial

#### Características Principales
- **Dashboard Web Completo** en http://localhost:5555
  - Upload múltiple de archivos con drag & drop
  - Procesamiento de URLs (YouTube, TikTok, Instagram, Twitter/X, Vimeo)
  - Wizard de configuración inicial para IA local o API externa
  - Logs en tiempo real vía WebSocket
  - Previsualización de clips finales
  - Botón de aprobación y subida a YouTube

- **Pipeline de 11 Etapas Asíncronas**
  1. Detección de nuevos vídeos (Watch Folder)
  2. Transcodificación a MP4 H.264/AAC
  3. Transcripción local con faster-whisper
  4. Extracción de highlights con LLM del usuario
  5. Limpieza de guion (muletillas, retakes)
  6. Corte físico con alineación word-level
  7. Smart crop 9:16 con detección de caras
  8. Planificación de animaciones con LLM
  9. Animación segmentada (sesiones frescas <15s)
  10. Composición final (subtítulos karaoke, música con ducking)
  11. Validación y subida opcional

- **Arquitectura 100% Agnóstica a IA**
  - Cliente HTTP unificado usando solo `requests`
  - Compatible con CUALQUIER servidor LLM local (/v1/chat/completions)
  - Compatible con CUALQUIER proveedor de API externo
  - CERO SDKs propietarios hardcodeados

- **Launcher con Botón de Inicio**
  - GUI nativa con Tkinter (Windows/macOS/Linux)
  - Modo CLI automático si no hay display
  - Indicador de estado del servidor
  - Acceso directo al dashboard
  - Logs integrados

- **Scripts de Empaquetado Multiplataforma**
  - Windows: `build_windows.bat` → VIDEOAI.exe + installer.iss
  - macOS: `build_macos.sh` + `setup_macos.py` → VIDEOAI.app
  - Linux: `build_linux.sh` → VIDEOAI.AppImage

#### Documentación
- README.md - Descripción completa del proyecto
- INSTALL.md - Guías de instalación para Windows/macOS/Linux
- QUICKSTART.md - Guía rápida de 30 segundos
- RELEASE_CHECKLIST.md - Lista de verificación para releases
- CHANGELOG.md - Historial de cambios

#### Configuración
- .env.example - Plantilla de configuración
- config.yaml - Valores por defecto
- .gitignore - Archivos excluidos del repositorio
- LICENSE - Licencia MIT

### 🔧 Componentes Técnicos

#### Helpers
- `llm_client.py` - Cliente HTTP agnóstico para LLMs
- `stt_engine.py` - Wrapper para faster-whisper
- `timestamp_aligner.py` - Alineación word-level precisa
- `video_processor.py` - Procesamiento de vídeo (crop, subtítulos, ducking)
- `animation_executor.py` - Ejecutor de animaciones segmentadas
- `file_watcher.py` - Monitor de carpeta de entrada
- `uploader.py` - Subida a YouTube y otras plataformas

#### Prompts
- `highlight_extraction.md` - Extracción de momentos virales
- `script_cleanup.md` - Limpieza de guion
- `animation_plan.md` - Planificación de animaciones
- `thumbnail_title.md` - Generación de thumbnails y títulos
- `metadata_gen.md` - Metadatos para redes sociales

### 📦 Stack Tecnológico
- **Backend**: FastAPI, Uvicorn, WebSockets
- **Frontend**: Jinja2, Vanilla JS, CSS3
- **Vídeo**: FFmpeg, OpenCV, Pillow
- **Audio**: faster-whisper, scipy, numpy
- **IA**: requests HTTP (agnóstico)
- **Utilidades**: pydantic-settings, pyyaml, python-dotenv, watchdog, aiofiles

### 🚀 Requisitos del Sistema
- Python 3.9+
- FFmpeg instalado en PATH
- 8GB RAM mínimo (16GB recomendado)
- GPU NVIDIA opcional (para aceleración CUDA en whisper)

---

## [Unreleased]

### Planeado para Futuras Versiones
- Soporte para más plataformas de vídeo online
- Plantillas de animación personalizables desde el Dashboard
- Exportar/importar presets de configuración
- Modo batch para procesar colas de vídeos
- Integración con más redes sociales (Twitch, LinkedIn)
- Editor de clips post-procesamiento
- Estadísticas y analytics de rendimiento
- Sistema de plugins/extensions

---

## Notas de Versión

### Convenciones de Versionado
- **MAJOR** (X.0.0): Cambios incompatibles hacia atrás
- **MINOR** (x.Y.0): Nuevas características compatibles
- **PATCH** (x.y.Z): Correcciones de bugs compatibles

### Canales de Distribución
- GitHub Releases: https://github.com/tu-usuario/videoai/releases
- PyPI: Próximamente
- Docker Hub: Próximamente

---

Para más información, visitar: https://github.com/tu-usuario/videoai
