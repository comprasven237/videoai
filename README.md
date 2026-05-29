--- README.md (原始)
# 🎬 Video Automator - Sistema de Producción de Vídeo Automatizado

Sistema completo de producción de vídeo automatizado con arquitectura híbrida (Local LLM + API externa configurable), inspirado en el patrón "Tú grabas, la IA edita y anima".

## 📋 Descripción

Transforma vídeos crudos (horizontales o verticales, 5-60 min) en clips virales verticales (9:16) de 30 a 90 segundos, listos para TikTok, Reels y Shorts.

### Flujo Completo
```
Grabación → Transcripción → Limpieza IA → Recorte Físico → Animación Segmentada → Render → Upload Opcional
```

## 🏗️ Arquitectura

El sistema sigue el **patrón de 3 carpetas de Iván Prats**:

```
project_root/
├── packaging/     # Ideas, guiones, thumbnails, títulos (input creativo)
├── cleaning/      # Vídeo crudo → vídeo limpio (STT + corte IA)
└── animation/     # Plan de animación → assets → composición final
```

### Separación Crítica: IA vs Código Determinista

| Tarea | Implementación | Razón |
|-------|---------------|-------|
| Extraer highlights | LLM (no-determinista) | Requiere juicio creativo |
| Limpiar guion | LLM (no-determinista) | Mantener tono auténtico |
| Planificar animaciones | LLM (no-determinista) | Creatividad visual |
| Cortar vídeo | FFmpeg (determinista) | Precisión frame-perfect |
| Smart crop | OpenCV (determinista) | Algoritmos de visión |
| Render final | FFmpeg (determinista) | Consistencia garantizada |

## 🚀 Instalación

### Requisitos Previos

- Python 3.10+
- FFmpeg instalado y en PATH
- Ollama/vLLM/LM Studio (para modo local) O API key (para modo externo)

### Pasos de Instalación

```bash
# 1. Clonar/navegar al directorio
cd /workspace

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env según tu configuración

# 5. Iniciar servidor
python main.py
```

### Acceso al Dashboard

Abre tu navegador en: **http://localhost:5555**

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# Modo de operación del LLM
LLM_MODE=local          # local | api
LLM_ENDPOINT=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
API_KEY=                # Solo si LLM_MODE=api

# Configuración STT
STT_MODEL_SIZE=base     # tiny, base, small, medium, large

# Output
OUTPUT_DURATION_MIN=30
OUTPUT_DURATION_MAX=90
RESOLUTION=1080x1920

# Rutas
WATCH_FOLDER=/workspace/cleaning/raw

# Upload
YOUTUBE_UPLOAD_ENABLED=false
```

### Configuración Avanzada (config.yaml)

```yaml
llm:
  mode: "local"
  endpoint: "http://localhost:11434/v1"
  model: "llama3.1:8b"
  timeout: 60
  max_retries: 2

stt:
  model_size: "base"
  device: "cpu"
  compute_type: "int8"

output:
  duration_min: 30
  duration_max: 90
  resolution: "1080x1920"
  video_bitrate: "8M"

animation:
  segment_max_duration: 15  # Segundos por segmento
  max_concurrent_segments: 3
```

## 📖 Uso

### Método 1: Dashboard Web (Recomendado)

1. Abre http://localhost:5555
2. Haz clic en "📁 Seleccionar Vídeo"
3. Elige tu archivo de vídeo
4. Presiona "🚀 INICIAR PROCESO"
5. Monitorea el progreso en tiempo real
6. Descarga o aprueba el resultado final

### Método 2: Watch Folder

Coloca vídeos en `/workspace/cleaning/raw/` y el sistema los detectará automáticamente.

### Pipeline de 11 Etapas

| Etapa | Nombre | Descripción |
|-------|--------|-------------|
| 1 | Ingesta | Validación y copia del vídeo |
| 2 | Transcodificación | Conversión a H.264/AAC estándar |
| 3 | STT | Transcripción palabra-por-palabra con Whisper |
| 4 | Highlights | Extracción de segmentos virales con LLM |
| 5 | Limpieza Guion | Eliminación de muletillas/redundancias |
| 6 | Alineación y Corte | Corte preciso basado en timestamps |
| 7 | Smart Crop 9:16 | Recorte inteligente a vertical |
| 8 | Plan Animación | Generación de plan de animaciones |
| 9 | Animación Segmentada | Ejecución por segmentos (<15s cada uno) |
| 10 | Composición | Ensamblaje final con subtítulos |
| 11 | Validación | Verificación de duración y calidad |

## 🔧 Componentes Principales

### helpers/llm_client.py
Cliente HTTP unificado para LLM (local o API). Soporta:
- Ollama, vLLM, LM Studio (modo local)
- APIs compatibles con OpenAI (modo externo)
- Reintentos automáticos con backoff exponencial
- Parseo robusto de JSON

### helpers/stt_engine.py
Motor de Speech-to-Text usando faster-whisper:
- Transcripción palabra-por-palabra
- Timestamps precisos en milisegundos
- Detección automática de idioma
- Filtro VAD para mejor precisión

### helpers/timestamp_aligner.py
Alineación difusa entre guion limpio y transcripción original:
- Algoritmo SequenceMatcher para matching
- Cortes frame-perfect con FFmpeg
- Fusión inteligente de segmentos adyacentes

### helpers/video_processor.py
Procesamiento de vídeo avanzado:
- `smart_crop_9_16`: Detección de caras + tracking
- `burn_karaoke_subtitles`: Subtítulos estilo karaoke
- `apply_audio_ducking`: Compresión sidechain
- `validate_duration`: Validación estricta 30-90s

### helpers/animation_executor.py
Patrón de animación segmentada:
- Divide plan en segmentos <15 segundos
- Ejecuta LLM en sesión fresca por segmento
- Evita degradación por contexto largo
- Ensambla resultados determinísticamente

### pipeline.py
Orquestador asíncrono del pipeline completo:
- Gestión de estado persistente
- Callbacks para progreso en tiempo real
- Recuperación de procesos interrumpidos
- Logging estructurado por etapa

## 🌐 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard web |
| `/api/start` | POST | Iniciar pipeline |
| `/api/status/{session_id}` | GET | Estado del proceso |
| `/api/pipelines` | GET | Listar pipelines activos |
| `/ws/logs` | WebSocket | Logs en tiempo real |
| `/output/latest.mp4` | GET | Último vídeo generado |
| `/api/config` | GET/POST | Configuración del sistema |

## 📁 Estructura de Directorios

```
/workspace
├── config.py              # Configuración unificada Pydantic
├── main.py                # Servidor FastAPI
├── pipeline.py            # Orquestador del pipeline
├── helpers/
│   ├── llm_client.py
│   ├── stt_engine.py
│   ├── timestamp_aligner.py
│   ├── video_processor.py
│   ├── animation_executor.py
│   ├── file_watcher.py
│   └── uploader.py
├── prompts/               # System prompts para LLM
├── templates/             # HTML dashboard
├── static/                # CSS/JS frontend
├── cleaning/raw/          # Watch folder para vídeos
├── output/                # Clips finales
└── state/                 # Estados persistentes
```

## 🔍 Solución de Problemas

### FFmpeg no encontrado
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Descargar de https://ffmpeg.org/download.html
# Añadir al PATH
```

### Error de conexión con LLM local
```bash
# Verificar que Ollama esté corriendo
ollama serve

# Verificar modelo disponible
ollama list

# Pull del modelo si falta
ollama pull llama3.1:8b
```

### Vídeos demasiado largos/cortos
Ajusta en `.env`:
```bash
OUTPUT_DURATION_MIN=30
OUTPUT_DURATION_MAX=90
```

### Memoria insuficiente para Whisper
Usa modelo más pequeño:
```bash
STT_MODEL_SIZE=tiny  # o base
```

## 📊 Métricas de Calidad

El sistema valida automáticamente:
- ✅ Duración: 30-90 segundos
- ✅ Bitrate mínimo: 8 Mbps
- ✅ Audio: -14 LUFS (estándar YouTube)
- ✅ Resolución: 1080x1920 (9:16)
- ✅ Subtítulos quemados: Sí
- ✅ Formato: MP4 H.264/AAC

## 🚨 Consideraciones Importantes

1. **Primera ejecución**: La descarga del modelo Whisper puede tardar varios minutos
2. **GPU opcional**: El sistema funciona en CPU, pero CUDA acelera significativamente
3. **Upload automático**: Requiere autenticación previa (cookies/netrc para yt-dlp)
4. **Contexto LLM**: Animación segmentada evita degradación en vídeos largos

## 📝 Licencia

Este proyecto es open source bajo licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea rama para feature (`git checkout -b feature/amazing`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push a rama (`git push origin feature/amazing`)
5. Abre Pull Request

---

**Desarrollado siguiendo las mejores prácticas de automatización de vídeo con IA.**

+++ README.md (修改后)
# 🎬 Video AI Automator - Sistema de Producción de Vídeo Automatizado

Sistema completo de producción de vídeo automatizado con **arquitectura híbrida agnóstica** (cualquier Local LLM + cualquier API externa compatible), inspirado en el patrón "Tú grabas, la IA edita y anima".

## 📋 Descripción

Transforma vídeos crudos (horizontales o verticales, 5-60 min) en clips virales verticales (9:16) de 30 a 90 segundos, listos para TikTok, Reels y Shorts.

### Flujo Completo
```
Grabación → Transcripción → Limpieza IA → Recorte Físico → Animación Segmentada → Render → Upload Opcional
```

## 🚀 Instalación Rápida

### Windows

```powershell
# Descargar el proyecto
git clone https://github.com/tu-usuario/videoai.git
cd videoai

# Ejecutar instalador automático (como Administrador)
.\install_windows.ps1
```

El instalador de Windows:
- ✅ Verifica e instala Python 3.12 si es necesario
- ✅ Instala FFmpeg automáticamente
- ✅ Crea entorno virtual
- ✅ Instala todas las dependencias
- ✅ Crea acceso directo en el escritorio

### macOS

```bash
# Descargar el proyecto
git clone https://github.com/tu-usuario/videoai.git
cd videoai

# Hacer ejecutable e instalar
chmod +x install_macos.sh
./install_macos.sh
```

El instalador de macOS:
- ✅ Verifica e instala Homebrew si es necesario
- ✅ Instala Python 3.12 y FFmpeg vía Homebrew
- ✅ Crea entorno virtual
- ✅ Instala todas las dependencias
- ✅ Crea aplicación nativa `Video AI Automator.app`
- ✅ Agrega alias `videoai` a tu shell

### Linux (Manual)

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/videoai.git
cd videoai

# Instalar dependencias del sistema
sudo apt-get update && sudo apt-get install -y python3 python3-pip ffmpeg

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias Python
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env
```

## 🏗️ Arquitectura

El sistema sigue el **patrón de 3 carpetas de Iván Prats**:

```
project_root/
├── packaging/     # Ideas, guiones, thumbnails, títulos (input creativo)
├── cleaning/      # Vídeo crudo → vídeo limpio (STT + corte IA)
└── animation/     # Plan de animación → assets → composición final
```

### Separación Crítica: IA vs Código Determinista

| Tarea | Implementación | Razón |
|-------|---------------|-------|
| Extraer highlights | LLM (no-determinista) | Requiere juicio creativo |
| Limpiar guion | LLM (no-determinista) | Mantener tono auténtico |
| Planificar animaciones | LLM (no-determinista) | Creatividad visual |
| Cortar vídeo | FFmpeg (determinista) | Precisión frame-perfect |
| Smart crop | OpenCV (determinista) | Algoritmos de visión |
| Render final | FFmpeg (determinista) | Consistencia garantizada |

## 🚀 Instalación

### Requisitos Previos

- Python 3.10+
- FFmpeg instalado y en PATH
- Ollama/vLLM/LM Studio (para modo local) O API key (para modo externo)

### Pasos de Instalación

```bash
# 1. Clonar/navegar al directorio
cd /workspace

# 2. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env según tu configuración

# 5. Iniciar servidor
python main.py
```

### Acceso al Dashboard

Abre tu navegador en: **http://localhost:5555**

## 🔄 Proveedores LLM Soportados

El sistema es **100% agnóstico** y funciona con cualquier proveedor compatible con el formato OpenAI API.

### Locales (sin API Key)

| Proveedor | Endpoint por defecto | Modelos recomendados |
|-----------|---------------------|----------------------|
| **Ollama** | `http://localhost:11434/v1` | llama3.1:8b, mistral, gemma2 |
| **vLLM** | `http://localhost:5000/v1` | Cualquier modelo HF |
| **LM Studio** | `http://localhost:1234/v1` | Modelos locales GGUF |
| **Text Generation WebUI** | `http://localhost:5000/v1` | Cualquier modelo |

### APIs Externas (con API Key)

| Proveedor | Endpoint | Notas |
|-----------|----------|-------|
| **OpenAI** | `https://api.openai.com/v1` | gpt-4o, gpt-4-turbo, gpt-3.5-turbo |
| **Groq** | `https://api.groq.com/openai/v1` | Ultra-rápido, gratis con límites |
| **Together AI** | `https://api.together.xyz/v1` | Amplia variedad de modelos |
| **Fireworks AI** | `https://api.fireworks.ai/inference/v1` | Modelos optimizados |
| **Cerebras** | `https://api.cerebras.ai/v1` | Inferencia acelerada |
| **DeepSeek** | `https://api.deepseek.com/v1` | Modelos chinos de alta calidad |
| **Any Other** | Tu endpoint personalizado | Compatible con OpenAI API |

### Configuración para cada proveedor

```bash
# Ollama (Local - Gratis)
LLM_MODE=local
LLM_ENDPOINT=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
API_KEY=

# Groq (API - Gratis con límites)
LLM_MODE=api
LLM_ENDPOINT=https://api.groq.com/openai/v1
LLM_MODEL=llama3-70b-8192
API_KEY=gsk_...

# OpenAI (API - Pago)
LLM_MODE=api
LLM_ENDPOINT=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
API_KEY=sk-...

# Together AI (API - Pago económico)
LLM_MODE=api
LLM_ENDPOINT=https://api.together.xyz/v1
LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
API_KEY=...
```

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# Modo de operación del LLM
LLM_MODE=local          # local | api
LLM_ENDPOINT=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
API_KEY=                # Solo si LLM_MODE=api

# Configuración STT
STT_MODEL_SIZE=base     # tiny, base, small, medium, large

# Output
OUTPUT_DURATION_MIN=30
OUTPUT_DURATION_MAX=90
RESOLUTION=1080x1920

# Rutas
WATCH_FOLDER=/workspace/cleaning/raw

# Upload
YOUTUBE_UPLOAD_ENABLED=false
```

### Configuración Avanzada (config.yaml)

```yaml
llm:
  mode: "local"
  endpoint: "http://localhost:11434/v1"
  model: "llama3.1:8b"
  timeout: 60
  max_retries: 2

stt:
  model_size: "base"
  device: "cpu"
  compute_type: "int8"

output:
  duration_min: 30
  duration_max: 90
  resolution: "1080x1920"
  video_bitrate: "8M"

animation:
  segment_max_duration: 15  # Segundos por segmento
  max_concurrent_segments: 3
```

## 📖 Uso

### Método 1: Dashboard Web (Recomendado)

1. Abre http://localhost:5555
2. Haz clic en "📁 Seleccionar Vídeo"
3. Elige tu archivo de vídeo
4. Presiona "🚀 INICIAR PROCESO"
5. Monitorea el progreso en tiempo real
6. Descarga o aprueba el resultado final

### Método 2: Watch Folder

Coloca vídeos en `/workspace/cleaning/raw/` y el sistema los detectará automáticamente.

### Pipeline de 11 Etapas

| Etapa | Nombre | Descripción |
|-------|--------|-------------|
| 1 | Ingesta | Validación y copia del vídeo |
| 2 | Transcodificación | Conversión a H.264/AAC estándar |
| 3 | STT | Transcripción palabra-por-palabra con Whisper |
| 4 | Highlights | Extracción de segmentos virales con LLM |
| 5 | Limpieza Guion | Eliminación de muletillas/redundancias |
| 6 | Alineación y Corte | Corte preciso basado en timestamps |
| 7 | Smart Crop 9:16 | Recorte inteligente a vertical |
| 8 | Plan Animación | Generación de plan de animaciones |
| 9 | Animación Segmentada | Ejecución por segmentos (<15s cada uno) |
| 10 | Composición | Ensamblaje final con subtítulos |
| 11 | Validación | Verificación de duración y calidad |

## 🔧 Componentes Principales

### helpers/llm_client.py
Cliente HTTP unificado para LLM (local o API). Soporta:
- Ollama, vLLM, LM Studio (modo local)
- APIs compatibles con OpenAI (modo externo)
- Reintentos automáticos con backoff exponencial
- Parseo robusto de JSON

### helpers/stt_engine.py
Motor de Speech-to-Text usando faster-whisper:
- Transcripción palabra-por-palabra
- Timestamps precisos en milisegundos
- Detección automática de idioma
- Filtro VAD para mejor precisión

### helpers/timestamp_aligner.py
Alineación difusa entre guion limpio y transcripción original:
- Algoritmo SequenceMatcher para matching
- Cortes frame-perfect con FFmpeg
- Fusión inteligente de segmentos adyacentes

### helpers/video_processor.py
Procesamiento de vídeo avanzado:
- `smart_crop_9_16`: Detección de caras + tracking
- `burn_karaoke_subtitles`: Subtítulos estilo karaoke
- `apply_audio_ducking`: Compresión sidechain
- `validate_duration`: Validación estricta 30-90s

### helpers/animation_executor.py
Patrón de animación segmentada:
- Divide plan en segmentos <15 segundos
- Ejecuta LLM en sesión fresca por segmento
- Evita degradación por contexto largo
- Ensambla resultados determinísticamente

### pipeline.py
Orquestador asíncrono del pipeline completo:
- Gestión de estado persistente
- Callbacks para progreso en tiempo real
- Recuperación de procesos interrumpidos
- Logging estructurado por etapa

## 🌐 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard web |
| `/api/start` | POST | Iniciar pipeline |
| `/api/status/{session_id}` | GET | Estado del proceso |
| `/api/pipelines` | GET | Listar pipelines activos |
| `/ws/logs` | WebSocket | Logs en tiempo real |
| `/output/latest.mp4` | GET | Último vídeo generado |
| `/api/config` | GET/POST | Configuración del sistema |

## 📁 Estructura de Directorios

```
/workspace
├── config.py              # Configuración unificada Pydantic
├── main.py                # Servidor FastAPI
├── pipeline.py            # Orquestador del pipeline
├── helpers/
│   ├── llm_client.py
│   ├── stt_engine.py
│   ├── timestamp_aligner.py
│   ├── video_processor.py
│   ├── animation_executor.py
│   ├── file_watcher.py
│   └── uploader.py
├── prompts/               # System prompts para LLM
├── templates/             # HTML dashboard
├── static/                # CSS/JS frontend
├── cleaning/raw/          # Watch folder para vídeos
├── output/                # Clips finales
└── state/                 # Estados persistentes
```

## 🔍 Solución de Problemas

### FFmpeg no encontrado
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Descargar de https://ffmpeg.org/download.html
# Añadir al PATH
```

### Error de conexión con LLM local
```bash
# Verificar que Ollama esté corriendo
ollama serve

# Verificar modelo disponible
ollama list

# Pull del modelo si falta
ollama pull llama3.1:8b
```

### Vídeos demasiado largos/cortos
Ajusta en `.env`:
```bash
OUTPUT_DURATION_MIN=30
OUTPUT_DURATION_MAX=90
```

### Memoria insuficiente para Whisper
Usa modelo más pequeño:
```bash
STT_MODEL_SIZE=tiny  # o base
```

## 📊 Métricas de Calidad

El sistema valida automáticamente:
- ✅ Duración: 30-90 segundos
- ✅ Bitrate mínimo: 8 Mbps
- ✅ Audio: -14 LUFS (estándar YouTube)
- ✅ Resolución: 1080x1920 (9:16)
- ✅ Subtítulos quemados: Sí
- ✅ Formato: MP4 H.264/AAC

## 🚨 Consideraciones Importantes

1. **Primera ejecución**: La descarga del modelo Whisper puede tardar varios minutos
2. **GPU opcional**: El sistema funciona en CPU, pero CUDA acelera significativamente
3. **Upload automático**: Requiere autenticación previa (cookies/netrc para yt-dlp)
4. **Contexto LLM**: Animación segmentada evita degradación en vídeos largos

## 📝 Licencia

Este proyecto es open source bajo licencia MIT.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea rama para feature (`git checkout -b feature/amazing`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push a rama (`git push origin feature/amazing`)
5. Abre Pull Request

---

**Desarrollado siguiendo las mejores prácticas de automatización de vídeo con IA.**