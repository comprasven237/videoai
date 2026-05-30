# 🎬 VIDEOAI - Sistema de Producción de Vídeo Automatizado

## Descripción

VIDEOAI es un sistema completo de producción de vídeo automatizado con arquitectura híbrida (LLM Local configurable + API externa configurable), inspirado en el patrón "Tú grabas, la IA edita y anima".

Transforma vídeos crudos (horizontales o verticales, 5-60 min) en clips virales verticales (9:16) de 30 a 90 segundos listos para TikTok, Reels y Shorts.

## ⚠️ PRINCIPIO FUNDAMENTAL: SISTEMA 100% AGNÓSTICO A LA IA

**Este sistema NUNCA asume qué herramienta de IA usa el usuario.**

Tanto el servidor LLM local como el servicio de API externo son configurados por el propio usuario al momento de iniciar el sistema por primera vez (o desde el panel de configuración del Dashboard).

### MODO LOCAL
El sistema se conecta a CUALQUIER servidor local que exponga un endpoint compatible con el formato `/v1/chat/completions`:
- Ollama
- LM Studio  
- vLLM
- Text Generation WebUI
- Cualquier otro servidor compatible con OpenAI API format

### MODO API
El sistema se conecta a CUALQUIER proveedor de API que exponga un endpoint compatible:
- OpenAI
- Anthropic
- Google AI
- Mistral
- Cohere
- Cualquier otro proveedor con formato estándar

**REGLA ABSOLUTA:** El código NO hardcodea ni asume ningún proveedor, modelo o URL específica. Todos los campos son libres y los completa el usuario.

---

## 🚀 Flujo de Producción (11 Etapas)

```
┌─────────────────────────────────────────────────────────────────┐
│  ETAPA 1  [INGESTA]      Watcher detecta nuevo vídeo            │
│  ETAPA 2  [TRANSCODIF.]  ffmpeg → MP4 H.264/AAC, 30fps          │
│  ETAPA 3  [STT LOCAL]    faster-whisper → JSON con timestamps   │
│  ETAPA 4  [HIGHLIGHTS]   LLM → Extrae momentos virales          │
│  ETAPA 5  [LIMPIEZA]     LLM → Elimina muletillas, retakes      │
│  ETAPA 6  [CORTE FÍSICO] timestamp_aligner → cortes exactos     │
│  ETAPA 7  [SMART CROP]   OpenCV → 1080x1920 (9:16)              │
│  ETAPA 8  [PLAN ANIM.]   LLM → animation_plan.json              │
│  ETAPA 9  [ANIMACIÓN]    Sesión LLM fresca por segmento <15s    │
│  ETAPA 10 [COMPOSICIÓN]  Ensambla vídeo + animaciones + subs    │
│  ETAPA 11 [VALIDACIÓN]   ffprobe valida → upload opcional       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
VIDEOAI/
├── config.py              # Configuración con Pydantic Settings
├── .env.example           # Plantilla de variables de entorno
├── config.yaml            # Valores por defecto
├── requirements.txt       # Dependencias Python
├── main.py                # FastAPI + Dashboard + WebSockets
├── pipeline.py            # Orquestador de 11 etapas
│
├── helpers/
│   ├── __init__.py
│   ├── llm_client.py      # Cliente HTTP puro (requests), agnóstico
│   ├── stt_engine.py      # Wrapper faster-whisper
│   ├── timestamp_aligner.py  # Word-level alignment
│   ├── video_processor.py # Crop, subtítulos, ducking
│   ├── animation_executor.py # Animación segmentada
│   ├── file_watcher.py    # Watch folder pattern
│   └── uploader.py        # YouTube upload (opcional)
│
├── prompts/
│   ├── highlight_extraction.md
│   ├── script_cleanup.md
│   ├── animation_plan.md
│   ├── thumbnail_title.md
│   └── metadata_gen.md
│
├── templates/
│   ├── setup_wizard.html  # Wizard de configuración inicial
│   └── index.html         # Dashboard principal
│
├── static/
│   ├── style.css
│   └── app.js
│
├── packaging/             # Ideas, guiones, thumbnails
├── cleaning/
│   ├── raw/               # Vídeos crudos de entrada
│   ├── transcriptions/    # Transcripciones JSON
│   └── cleaned/           # Vídeos limpiados
├── animation/
│   ├── plans/             # Animation plans JSON
│   ├── segments/          # Assets de animación
│   └── composed/          # Vídeos compuestos
├── output/                # Clips finales
├── assets/                # Recursos adicionales
├── logs/                  # Logs del sistema
└── state/                 # Estado para reanudación
```

---

## 🔧 Instalación

### Requisitos Previos

- Python 3.10+
- FFmpeg instalado en el sistema
- GPU NVIDIA recomendada (para faster-whisper)

### Pasos de Instalación

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd VIDEOAI

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Iniciar el sistema
python main.py
```

### Primer Uso

Al ejecutar `main.py` por primera vez:

1. El Dashboard se abre en `http://localhost:5555`
2. Se muestra automáticamente el **Wizard de Configuración**
3. Configura tu modo de IA (Local o API)
4. Ingresa los datos de tu endpoint/modelo
5. Prueba la conexión
6. Guarda y comienza a usar

---

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# MODO DE IA: "local" o "api"
LLM_MODE=local

# URL del endpoint (servidor local o proveedor API)
LLM_ENDPOINT=http://localhost:1234/v1

# Nombre del modelo a usar
LLM_MODEL=llama-2-7b

# API Key (dejar vacío si es modo local)
LLM_API_KEY=

# Modelo de Speech-to-Text
STT_MODEL_SIZE=base

# Duración objetivo del clip final (segundos)
OUTPUT_DURATION_MIN=30
OUTPUT_DURATION_MAX=90

# Resolución de output (vertical 9:16)
RESOLUTION=1080x1920

# Carpeta de entrada de vídeos crudos
WATCH_FOLDER=./cleaning/raw

# Subida automática a YouTube
YOUTUBE_UPLOAD_ENABLED=false

# Puerto del Dashboard
DASHBOARD_PORT=5555
```

---

## 🎯 Características Principales

### 1. Backend Dual Configurable (Agnóstico)
- Cliente HTTP unificado usando SOLO `requests`
- CERO SDKs propietarios
- Compatible con cualquier endpoint `/v1/chat/completions`

### 2. Separación Crítica IA vs Código Determinista
- **IA**: Tareas creativas no-deterministas (highlights, limpieza, plan de animación)
- **Helpers Python**: Tareas mecánicas (cortar, alinear, renderizar) SIN consumo de tokens

### 3. Watch Folder Pattern
- Monitoreo automático de `/cleaning/raw/`
- Disparo asíncrono del pipeline al detectar nuevo vídeo
- Estado persistente para reanudar procesos interrumpidos

### 4. Animación Segmentada (Evita Degradación de Contexto)
- Plan de animación generado por IA
- Cada segmento <15s se procesa en sesión LLM FRESCA
- Resultados ensamblados determinísticamente

### 5. Alineación Word-Level Timestamp
- faster-whisper genera timestamps por palabra
- Comparación difusa guion limpio vs transcripción original
- Cortes exactos en milisegundos (frame-perfect)

### 6. Interfaz Única (Dashboard)
- Wizard de configuración inicial
- Botón gigante "🚀 INICIAR PROCESO"
- Barra de progreso detallada
- Logs en tiempo real vía WebSockets
- Previsualización del clip final

---

## 🔌 Ejemplos de Configuración

### Servidor Local con Ollama

```env
LLM_MODE=local
LLM_ENDPOINT=http://localhost:11434/v1
LLM_MODEL=llama2
LLM_API_KEY=
```

### Servidor Local con LM Studio

```env
LLM_MODE=local
LLM_ENDPOINT=http://localhost:1234/v1
LLM_MODEL=local-model
LLM_API_KEY=
```

### API Externa (OpenAI)

```env
LLM_MODE=api
LLM_ENDPOINT=https://api.openai.com/v1
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-...
```

### API Externa (Anthropic)

```env
LLM_MODE=api
LLM_ENDPOINT=https://api.anthropic.com/v1
LLM_MODEL=claude-3-opus-20240229
LLM_API_KEY=sk-ant-...
```

---

## 📊 Métricas Técnicas

| Parámetro | Valor |
|-----------|-------|
| Duración Output | 30-90 segundos (configurable) |
| Resolución | 1080x1920 (9:16 vertical) |
| Bitrate Mínimo | 8 Mbps |
| Audio | -14 LUFS |
| FPS | 30 |
| Codecs | H.264 (vídeo), AAC (audio) |
| Subtítulos | Quemados estilo karaoke |

---

## 🛠️ Stack Técnico

### Python Libraries
- **Web Framework**: fastapi, uvicorn, websockets, jinja2
- **Config**: pydantic-settings, pyyaml, python-dotenv
- **Vídeo/Audio**: faster-whisper, ffmpeg-python, opencv-python, pillow
- **Utilidades**: requests, numpy, scipy, watchdog
- **Upload**: selenium, webdriver-manager (opcional)

**Todo LLM va por requests HTTP puros.**

---

## 🔒 Seguridad

- API keys se guardan en `.env` (no versionar en git)
- Las keys no se exponen en logs ni respuestas
- WebSocket connections validadas por origen
- File watcher limitado a carpeta específica

---

## 🐛 Solución de Problemas

### El LLM no conecta
1. Verifica que el servidor/API esté corriendo
2. Prueba la URL en navegador: `{LLM_ENDPOINT}/chat/completions`
3. Usa el botón "Probar conexión" en el Dashboard
4. Revisa logs para mensajes de error específicos

### faster-whisper falla
1. Verifica instalación: `pip show faster-whisper`
2. Para GPU: instala CUDA drivers y `pip install faster-whisper[cuda118]`
3. Para CPU: usa modelo más pequeño (`tiny` o `base`)

### FFmpeg no encontrado
- Linux: `sudo apt install ffmpeg`
- Mac: `brew install ffmpeg`
- Windows: Descargar de ffmpeg.org y agregar al PATH

### Pipeline se traba
1. Revisa `state/.pipeline_state.json` para ver última etapa completada
2. Reinicia el proceso desde esa etapa
3. Si persiste, borra el estado y reinicia desde cero

---

## 📝 Licencia

MIT License - Ver archivo LICENSE para detalles.

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crea branch para feature (`git checkout -b feature/amazing-feature`)
3. Commit cambios (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Abre Pull Request

---

## 📞 Soporte

Para issues, bugs o feature requests, abrir un issue en GitHub.

---

**VIDEOAI** - Transforma tu contenido largo en clips virales automáticamente.
