"""
VIDEOAI - Aplicación Principal
FastAPI + Dashboard + WebSockets + Wizard de Configuración
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Set

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import Config, config as global_config
from helpers.llm_client import UnifiedLLMClient
from helpers.file_watcher import FileWatcher
from pipeline import PipelineOrchestrator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(title="VIDEOAI", version="1.0.0")

# Montar estáticos y templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Estado global
active_pipelines: Dict[str, PipelineOrchestrator] = {}
websocket_connections: Set[WebSocket] = set()
file_watcher: Optional[FileWatcher] = None


# ============================================================================
# ENDPOINTS DE PÁGINAS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Página principal del Dashboard.
    Muestra wizard si no está configurado, o dashboard si ya lo está.
    """
    configured = global_config.is_fully_configured()
    
    if not configured:
        return templates.TemplateResponse("setup_wizard.html", {
            "request": request,
            "title": "VIDEOAI - Configuración Inicial"
        })
    
    # Verificar estado del LLM
    llm_client = UnifiedLLMClient()
    llm_status = llm_client.health_check()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "VIDEOAI - Dashboard",
        "llm_connected": llm_status.get("ok", False),
        "llm_mode": global_config.llm.mode or "no configurado",
        "watch_folder": global_config.paths.watch_folder
    })


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Página de configuración (accesible desde el ícono ⚙️)"""
    return templates.TemplateResponse("setup_wizard.html", {
        "request": request,
        "title": "VIDEOAI - Configuración",
        "current_config": {
            "mode": global_config.llm.mode,
            "endpoint": global_config.llm.endpoint,
            "model": global_config.llm.model,
            "has_api_key": bool(global_config.llm.api_key),
            "duration_min": global_config.video.output_duration_min,
            "duration_max": global_config.video.output_duration_max,
            "watch_folder": global_config.paths.watch_folder,
            "youtube_enabled": global_config.youtube.upload_enabled
        }
    })


# ============================================================================
# ENDPOINTS DE API - CONFIGURACIÓN
# ============================================================================

@app.post("/api/setup")
async def save_setup(request: Request):
    """Guarda la configuración del wizard"""
    try:
        data = await request.json()
        
        # Validar campos requeridos
        required = ["llm_mode", "llm_endpoint", "llm_model"]
        for field in required:
            if field not in data or not data[field]:
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        # Guardar en .env
        config_data = {
            "llm_mode": data["llm_mode"],
            "llm_endpoint": data["llm_endpoint"],
            "llm_model": data["llm_model"],
            "llm_api_key": data.get("llm_api_key", ""),
            "stt_model_size": data.get("stt_model_size", "base"),
            "output_duration_min": int(data.get("output_duration_min", 30)),
            "output_duration_max": int(data.get("output_duration_max", 90)),
            "resolution": data.get("resolution", "1080x1920"),
            "watch_folder": data.get("watch_folder", "./cleaning/raw"),
            "youtube_upload_enabled": data.get("youtube_upload_enabled", False),
            "dashboard_port": int(data.get("dashboard_port", 5555))
        }
        
        global_config.save_to_env(config_data)
        
        logger.info("Configuración guardada exitosamente")
        
        return {"success": True, "message": "Configuración guardada"}
        
    except Exception as e:
        logger.error(f"Error al guardar configuración: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/test-llm")
async def test_llm_connection():
    """Prueba la conexión con el endpoint LLM configurado"""
    llm_client = UnifiedLLMClient()
    result = llm_client.health_check()
    
    return JSONResponse(content=result)


# ============================================================================
# ENDPOINTS DE API - UPLOAD Y PROCESAMIENTO DE VIDEOS
# ============================================================================

import aiofiles
import shutil
from fastapi import UploadFile, Form

UPLOAD_FOLDER = Path("./cleaning/raw")
DOWNLOADS_FOLDER = Path("./downloads")

# Asegurar que las carpetas existen
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
DOWNLOADS_FOLDER.mkdir(parents=True, exist_ok=True)


@app.post("/api/upload")
async def upload_video(video: UploadFile, filename: str = Form(None)):
    """
    Sube un vídeo al servidor.
    Soporta múltiples archivos concurrentes.
    """
    try:
        # Validar tipo de archivo
        valid_types = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 
                      'video/x-matroska', 'video/webm']
        
        if not any(video.content_type and t in video.content_type for t in valid_types):
            return {
                "success": False,
                "error": f"Tipo de archivo no válido: {video.content_type}"
            }
        
        # Generar nombre único
        safe_filename = filename or video.filename
        if not safe_filename:
            safe_filename = f"video_{len(list(UPLOAD_FOLDER.glob('*.mp4'))):03d}.mp4"
        
        # Guardar archivo
        output_path = UPLOAD_FOLDER / safe_filename
        
        async with aiofiles.open(output_path, 'wb') as out_file:
            while True:
                chunk = await video.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                await out_file.write(chunk)
        
        logger.info(f"Vídeo subido: {safe_filename} ({output_path.stat().st_size} bytes)")
        
        return {
            "success": True,
            "message": f"Vídeo subido exitosamente",
            "video_path": str(output_path),
            "filename": safe_filename
        }
        
    except Exception as e:
        logger.error(f"Error al subir vídeo: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/process-url")
async def process_video_url(request: Request):
    """
    Procesa una URL de vídeo y lo descarga.
    Soporta: YouTube, Vimeo, Twitter/X, Instagram, TikTok, links directos.
    """
    try:
        data = await request.json()
        url = data.get("url", "").strip()
        
        if not url:
            raise HTTPException(status_code=400, detail="URL requerida")
        
        logger.info(f"Procesando URL: {url}")
        
        # Intentar descargar usando yt-dlp si está disponible
        video_path = None
        filename = None
        
        try:
            import subprocess
            
            # Generar nombre de archivo único
            timestamp = int(time.time())
            output_template = str(DOWNLOADS_FOLDER / f"video_{timestamp}.%(ext)s")
            
            # Configurar yt-dlp
            cmd = [
                "yt-dlp",
                "--format", "best[ext=mp4]/best",
                "--output", output_template,
                "--no-playlist",  # Solo descargar el vídeo, no playlists
                "--restrict-filenames",
                url
            ]
            
            # Ejecutar descarga
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Buscar el archivo descargado
                downloaded_files = list(DOWNLOADS_FOLDER.glob(f"video_{timestamp}.*"))
                if downloaded_files:
                    video_path = downloaded_files[0]
                    filename = video_path.name
                    
                    # Mover a watch folder
                    dest_path = UPLOAD_FOLDER / filename
                    shutil.move(str(video_path), str(dest_path))
                    
                    logger.info(f"Vídeo descargado: {filename}")
                    
                    return {
                        "success": True,
                        "message": "Vídeo descargado exitosamente",
                        "video_path": str(dest_path),
                        "filename": filename
                    }
            
            # Si falla yt-dlp, intentar como link directo
            raise Exception("yt-dlp falló o no disponible")
            
        except Exception as download_error:
            logger.warning(f"Descarga con yt-dlp falló: {download_error}")
            
            # Fallback: intentar como link directo con requests
            try:
                import requests
                
                timestamp = int(time.time())
                filename = f"video_{timestamp}.mp4"
                temp_path = DOWNLOADS_FOLDER / filename
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                response = requests.get(url, headers=headers, stream=True, timeout=60)
                
                if response.status_code == 200 and 'video' in response.headers.get('Content-Type', ''):
                    async with aiofiles.open(temp_path, 'wb') as f:
                        async for chunk in response.iter_content(chunk_size=1024*1024):
                            await f.write(chunk)
                    
                    # Mover a watch folder
                    dest_path = UPLOAD_FOLDER / filename
                    shutil.move(str(temp_path), str(dest_path))
                    
                    logger.info(f"Vídeo descargado (link directo): {filename}")
                    
                    return {
                        "success": True,
                        "message": "Vídeo descargado exitosamente",
                        "video_path": str(dest_path),
                        "filename": filename
                    }
            except Exception as direct_error:
                logger.error(f"Descarga directa también falló: {direct_error}")
            
            # Si todo falla, devolver error informativo
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo descargar el vídeo. Intenta con otro link o sube el archivo manualmente.\n\nSoporta: YouTube, Vimeo, Twitter/X, Instagram, TikTok, links directos .mp4"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar URL: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/queue")
async def get_upload_queue():
    """Obtiene la lista de vídeos en la carpeta de upload"""
    videos = []
    
    for ext in ['*.mp4', '*.mov', '*.avi', '*.mkv', '*.webm']:
        for file in UPLOAD_FOLDER.glob(ext):
            stat = file.stat()
            videos.append({
                "filename": file.name,
                "path": str(file),
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            })
    
    # Ordenar por fecha de modificación (más reciente primero)
    videos.sort(key=lambda v: -v['modified'])
    
    return {"videos": videos, "count": len(videos)}


@app.delete("/api/video/{filename}")
async def delete_video(filename: str):
    """Elimina un vídeo de la carpeta de upload"""
    try:
        file_path = UPLOAD_FOLDER / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        # Verificar que esté dentro de la carpeta permitida
        if not str(file_path.resolve()).startswith(str(UPLOAD_FOLDER.resolve())):
            raise HTTPException(status_code=400, detail="Ruta no válida")
        
        file_path.unlink()
        logger.info(f"Vídeo eliminado: {filename}")
        
        return {"success": True, "message": "Vídeo eliminado"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar vídeo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DE API - PIPELINE
# ============================================================================

@app.post("/api/start")
async def start_pipeline(request: Request, background_tasks: BackgroundTasks):
    """Inicia el pipeline de procesamiento"""
    try:
        data = await request.json()
        video_path = data.get("video_path")
        
        if not video_path:
            # Escanear watch folder para encontrar vídeos
            watcher = FileWatcher()
            existing_videos = watcher.scan_existing()
            
            if not existing_videos:
                raise HTTPException(
                    status_code=400,
                    detail="No se especificó vídeo y no hay vídeos en la watch folder"
                )
            
            video_path = existing_videos[0]
        
        # Crear sesión
        session_id = f"session_{len(active_pipelines) + 1:03d}"
        
        # Crear orchestrator
        orchestrator = PipelineOrchestrator()
        active_pipelines[session_id] = orchestrator
        
        # Ejecutar en background
        background_tasks.add_task(run_pipeline_async, orchestrator, video_path, session_id)
        
        logger.info(f"Pipeline iniciado: {session_id} para {video_path}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Procesando: {Path(video_path).name}"
        }
        
    except Exception as e:
        logger.error(f"Error al iniciar pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_pipeline_async(
    orchestrator: PipelineOrchestrator,
    video_path: str,
    session_id: str
):
    """Ejecuta el pipeline asíncronamente y notifica por WebSocket"""
    try:
        result = await orchestrator.run(video_path, session_id)
        
        # Notificar completación por WebSocket
        await broadcast_websocket({
            "type": "pipeline_complete",
            "session_id": session_id,
            "success": result.get("success", False),
            "output_path": result.get("output_path"),
            "stages": result.get("stages", [])
        })
        
    except Exception as e:
        logger.error(f"Pipeline falló: {e}")
        await broadcast_websocket({
            "type": "pipeline_error",
            "session_id": session_id,
            "error": str(e)
        })
    finally:
        # Limpiar pipeline activo
        if session_id in active_pipelines:
            del active_pipelines[session_id]


@app.get("/api/status/{session_id}")
async def get_pipeline_status(session_id: str):
    """Obtiene el estado de un pipeline específico"""
    if session_id not in active_pipelines:
        # Intentar cargar desde estado guardado
        orchestrator = PipelineOrchestrator()
        state = orchestrator._load_state()
        
        if state and state.get("session_id") == session_id:
            return {
                "session_id": session_id,
                "restored": True,
                "current_stage": state.get("current_stage", 0),
                "stages": state.get("stages", []),
                "logs": state.get("logs", [])
            }
        
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    orchestrator = active_pipelines[session_id]
    return orchestrator.get_status()


@app.post("/api/cancel/{session_id}")
async def cancel_pipeline(session_id: str):
    """Cancela un pipeline en ejecución"""
    if session_id not in active_pipelines:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    orchestrator = active_pipelines[session_id]
    orchestrator.request_cancel()
    
    return {"success": True, "message": "Cancelación solicitada"}


# ============================================================================
# WEBSOCKET PARA LOGS EN TIEMPO REAL
# ============================================================================

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket para streaming de logs en tiempo real"""
    await websocket.accept()
    websocket_connections.add(websocket)
    
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        websocket_connections.discard(websocket)


async def broadcast_websocket(message: Dict[str, Any]):
    """Envía mensaje a todos los clientes WebSocket conectados"""
    if websocket_connections:
        await asyncio.gather(
            *[conn.send_json(message) for conn in websocket_connections],
            return_exceptions=True
        )


# ============================================================================
# ENDPOINTS DE OUTPUT
# ============================================================================

@app.get("/output/latest.mp4")
async def get_latest_output():
    """Sirve el último vídeo generado"""
    output_dir = Path("./output")
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="No hay outputs generados")
    
    # Encontrar el MP4 más reciente
    mp4_files = list(output_dir.glob("*.mp4"))
    
    if not mp4_files:
        raise HTTPException(status_code=404, detail="No hay vídeos en output")
    
    latest = max(mp4_files, key=lambda p: p.stat().st_mtime)
    
    return FileResponse(
        str(latest),
        media_type="video/mp4",
        filename=latest.name
    )


@app.get("/output/list")
async def list_outputs():
    """Lista todos los outputs generados"""
    output_dir = Path("./output")
    
    if not output_dir.exists():
        return []
    
    outputs = []
    for mp4_file in sorted(output_dir.glob("*.mp4"), key=lambda p: -p.stat().st_mtime):
        stat = mp4_file.stat()
        outputs.append({
            "filename": mp4_file.name,
            "size_bytes": stat.st_size,
            "created_at": stat.st_ctime,
            "url": f"/output/{mp4_file.name}"
        })
    
    return outputs


@app.get("/output/{filename}")
async def get_output(filename: str):
    """Sirve un output específico"""
    file_path = Path("./output") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(str(file_path), media_type="video/mp4")


# ============================================================================
# INICIALIZACIÓN
# ============================================================================

def initialize_file_watcher():
    """Inicializa el file watcher para procesamiento automático"""
    global file_watcher
    
    def on_video_detected(video_path: str):
        """Callback cuando se detecta un nuevo vídeo"""
        logger.info(f"Vídeo detectado automáticamente: {video_path}")
        
        # Iniciar pipeline automáticamente
        async def start_auto():
            session_id = f"auto_{Path(video_path).stem}"
            orchestrator = PipelineOrchestrator()
            active_pipelines[session_id] = orchestrator
            
            await run_pipeline_async(orchestrator, video_path, session_id)
        
        # Usar run_coroutine_threadsafe para ejecutar en el event loop desde un thread
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(start_auto(), loop)
    
    file_watcher = FileWatcher()
    file_watcher.set_callback(on_video_detected)
    file_watcher.start()
    
    logger.info(f"File watcher iniciado en: {global_config.paths.watch_folder}")


@app.on_event("startup")
async def startup_event():
    """Se ejecuta al iniciar la aplicación"""
    logger.info("VIDEOAI iniciando...")
    
    # Asegurar que las carpetas existen
    global_config.paths.ensure_exists()
    
    # Inicializar file watcher
    initialize_file_watcher()
    
    logger.info(f"Dashboard disponible en http://localhost:{global_config.dashboard.port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Se ejecuta al detener la aplicación"""
    logger.info("VIDEOAI deteniéndose...")
    
    # Detener file watcher
    if file_watcher:
        file_watcher.stop()
    
    # Cancelar pipelines activos
    for session_id, orchestrator in active_pipelines.items():
        orchestrator.request_cancel()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = global_config.dashboard.port
    
    logger.info(f"Iniciando VIDEOAI en puerto {port}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
