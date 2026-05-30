"""
VIDEOAI - Pipeline Orquestador Asíncrono
Coordina las 11 etapas del proceso de producción de vídeo
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from config import Config, config as global_config
from helpers.llm_client import UnifiedLLMClient
from helpers.stt_engine import STTEngine
from helpers.timestamp_aligner import TimestampAligner
from helpers.video_processor import VideoProcessor, VideoDurationError
from helpers.animation_executor import AnimationExecutor
from helpers.uploader import YouTubeUploader

logger = logging.getLogger(__name__)


class PipelineStage:
    """Representa una etapa del pipeline"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.status = "pending"  # pending, running, completed, failed
        self.message = ""
        self.progress = 0  # 0-100
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "message": self.message,
            "progress": self.progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class PipelineOrchestrator:
    """
    Orquesta el pipeline completo de 11 etapas asíncronas.
    Soporta pausa y reanudación desde state/.pipeline_state.json
    """
    
    STAGES = [
        ("INGESTA", "Detectando nuevo vídeo"),
        ("TRANSCODIF.", "Normalizando formato y codec"),
        ("STT LOCAL", "Transcribiendo con Whisper"),
        ("HIGHLIGHTS", "Extrayendo momentos virales con IA"),
        ("LIMPIEZA", "Limpiando guion (muletillas, retakes)"),
        ("CORTE FÍSICO", "Cortando vídeo con precisión frame-perfect"),
        ("SMART CROP 9:16", "Recortando a formato vertical"),
        ("PLAN ANIM.", "Generando plan de animaciones con IA"),
        ("ANIM. SEGMENT.", "Creando assets de animación"),
        ("COMPOSICIÓN", "Ensamblando vídeo final"),
        ("VALIDACIÓN", "Validando y subiendo a YouTube")
    ]
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el orquestador.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or global_config
        self.session_id: str = ""
        self.video_path: str = ""
        self.stages: List[PipelineStage] = []
        self.current_stage: int = 0
        self.state_file: Path = Path("state/.pipeline_state.json")
        self.logs: List[str] = []
        self._cancel_requested = False
        
        # Inicializar helpers
        self.llm_client = UnifiedLLMClient(config)
        self.stt_engine = STTEngine(config)
        self.timestamp_aligner = TimestampAligner()
        self.video_processor = VideoProcessor(config)
        self.animation_executor = AnimationExecutor(config)
        self.youtube_uploader = YouTubeUploader(config)
    
    def _log(self, message: str):
        """Agrega un log al historial"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        logger.info(message)
    
    def _update_stage(
        self,
        stage_idx: int,
        status: str,
        message: str = "",
        progress: int = 0
    ):
        """Actualiza el estado de una etapa"""
        if 0 <= stage_idx < len(self.stages):
            stage = self.stages[stage_idx]
            stage.status = status
            stage.message = message
            stage.progress = progress
            
            if status == "running" and not stage.started_at:
                stage.started_at = datetime.now()
            elif status in ["completed", "failed"] and not stage.completed_at:
                stage.completed_at = datetime.now()
    
    def _save_state(self):
        """Guarda el estado actual para permitir reanudación"""
        state = {
            "session_id": self.session_id,
            "video_path": self.video_path,
            "current_stage": self.current_stage,
            "stages": [s.to_dict() for s in self.stages],
            "logs": self.logs[-100:],  # Últimos 100 logs
            "timestamp": datetime.now().isoformat()
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """Carga estado previo si existe"""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    async def run(
        self,
        video_path: str,
        session_id: Optional[str] = None,
        resume: bool = False
    ) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo.
        
        Args:
            video_path: Ruta al vídeo de entrada
            session_id: ID único de sesión (generado si None)
            resume: Si True, intenta reanudar desde estado guardado
        
        Returns:
            Dict con resultado del pipeline
        """
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.video_path = video_path
        
        self._log(f"Iniciando pipeline - Sesión: {self.session_id}")
        self._log(f"Vídeo de entrada: {video_path}")
        
        # Inicializar etapas
        self.stages = [
            PipelineStage(name, desc) for name, desc in self.STAGES
        ]
        
        # Intentar reanudar
        if resume:
            prev_state = self._load_state()
            if prev_state and prev_state.get("video_path") == video_path:
                self._log(f"Reanudando desde etapa {prev_state.get('current_stage', 0)}")
                self.current_stage = prev_state.get("current_stage", 0)
                self.logs.extend(prev_state.get("logs", []))
            else:
                self._log("No hay estado previo para reanudar")
        
        try:
            # Ejecutar etapas secuencialmente
            for i in range(self.current_stage, len(self.stages)):
                if self._cancel_requested:
                    self._log("Pipeline cancelado por usuario")
                    break
                
                self.current_stage = i
                self._update_stage(i, "running", "Iniciando...", 0)
                self._save_state()
                
                # Ejecutar etapa específica
                method_name = f"_stage_{i+1:02d}"
                method = getattr(self, method_name, None)
                
                if method:
                    await method()
                    self._update_stage(i, "completed", "Completado", 100)
                else:
                    self._update_stage(i, "failed", f"Método {method_name} no encontrado", 0)
                    break
                
                self._save_state()
            
            # Resultado final
            success = all(s.status == "completed" for s in self.stages)
            
            return {
                "success": success,
                "session_id": self.session_id,
                "output_path": self._get_output_path(),
                "stages": [s.to_dict() for s in self.stages],
                "logs": self.logs
            }
            
        except Exception as e:
            self._log(f"Error crítico: {e}")
            self._update_stage(self.current_stage, "failed", str(e), 0)
            self._save_state()
            
            return {
                "success": False,
                "session_id": self.session_id,
                "error": str(e),
                "stages": [s.to_dict() for s in self.stages],
                "logs": self.logs
            }
    
    def _get_output_path(self) -> str:
        """Obtiene la ruta del output final"""
        return f"./output/{self.session_id}_final.mp4"
    
    async def _stage_01_ingesta(self):
        """Etapa 1: Ingesta - Validar archivo de entrada"""
        self._log("Validando archivo de entrada...")
        
        path = Path(self.video_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.video_path}")
        
        # Obtener información del vídeo
        info = self.video_processor.get_video_info(self.video_path)
        
        self._log(f"Vídeo: {info['width']}x{info['height']}, {info['duration']:.2f}s, {info['fps']}fps")
    
    async def _stage_02_transcodif(self):
        """Etapa 2: Transcodificación - Normalizar a MP4 H.264/AAC"""
        self._log("Transcodificando vídeo...")
        
        output_path = f"./cleaning/cleaned/{self.session_id}_transcoded.mp4"
        
        metadata = self.video_processor.transcode(
            self.video_path,
            output_path,
            target_fps=self.config.video.fps
        )
        
        self._log(f"Transcodificación completada: {metadata['resolution']}")
    
    async def _stage_03_stt(self):
        """Etapa 3: STT - Transcripción con timestamps por palabra"""
        self._log("Transcribiendo audio con Whisper...")
        
        transcoded_path = f"./cleaning/cleaned/{self.session_id}_transcoded.mp4"
        output_json = f"./cleaning/transcriptions/{self.session_id}.json"
        
        result = self.stt_engine.transcribe_and_save(
            transcoded_path,
            output_json
        )
        
        self._log(f"Transcripción: {len(result['words'])} palabras, idioma: {result['language']}")
    
    async def _stage_04_highlights(self):
        """Etapa 4: Highlights - Extraer momentos virales con IA"""
        self._log("Extrayendo highlights virales con IA...")
        
        # Cargar transcripción
        trans_path = f"./cleaning/transcriptions/{self.session_id}.json"
        with open(trans_path, 'r', encoding='utf-8') as f:
            transcription = json.load(f)
        
        # Cargar prompt
        prompt_path = Path("prompts/highlight_extraction.md")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        else:
            system_prompt = "Extrae los mejores momentos virales del siguiente contenido."
        
        # Construir prompt con transcripción
        user_prompt = f"""
Transcripción completa del vídeo (duración: {transcription.get('duration', 0):.2f}s):

{transcription['text'][:15000]}  # Limitar tokens

Duración objetivo del clip: {self.config.video.output_duration_min}-{self.config.video.output_duration_max} segundos.

Responde SOLO con JSON en este formato:
[
    {{"start": 0.0, "end": 30.0, "reason": "...", "viral_score": 0.9}},
    ...
]
""".strip()
        
        # Llamar a IA
        highlights = await asyncio.to_thread(
            lambda: self.llm_client.chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
                json_mode=True
            )
        )
        
        # Guardar highlights
        highlights_path = f"./packaging/{self.session_id}_highlights.json"
        with open(highlights_path, 'w', encoding='utf-8') as f:
            json.dump(highlights, f, indent=2)
        
        self._log(f"Highlights extraídos: {len(highlights)} segmentos")
    
    async def _stage_05_limpieza(self):
        """Etapa 5: Limpieza - Eliminar muletillas y redundancias"""
        self._log("Limpiando guion con IA...")
        
        # Cargar transcripción
        trans_path = f"./cleaning/transcriptions/{self.session_id}.json"
        with open(trans_path, 'r', encoding='utf-8') as f:
            transcription = json.load(f)
        
        # Cargar prompt
        prompt_path = Path("prompts/script_cleanup.md")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        else:
            system_prompt = "Limpia este guion eliminando muletillas, repeticiones y contenido irrelevante."
        
        user_prompt = f"""
Transcripción original:
{transcription['text'][:15000]}

Devuelve el guion limpio como texto plano, sin marcas ni comentarios.
""".strip()
        
        # Llamar a IA
        clean_script = await asyncio.to_thread(
            lambda: self.llm_client.chat(
                prompt=user_prompt,
                system_prompt=system_prompt
            )
        )
        
        # Guardar guion limpio
        script_path = f"./cleaning/cleaned/{self.session_id}_script.txt"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(clean_script)
        
        self._log(f"Guion limpio: {len(clean_script)} caracteres")
    
    async def _stage_06_corte_fisico(self):
        """Etapa 6: Corte físico - Alinear y cortar con precisión"""
        self._log("Realizando corte físico con alineación word-level...")
        
        # Cargar guion limpio
        script_path = f"./cleaning/cleaned/{self.session_id}_script.txt"
        with open(script_path, 'r', encoding='utf-8') as f:
            clean_script = f.read()
        
        # Cargar transcripción original
        trans_path = f"./cleaning/transcriptions/{self.session_id}.json"
        with open(trans_path, 'r', encoding='utf-8') as f:
            transcription = json.load(f)
        
        # Vídeo transcoded
        video_path = f"./cleaning/cleaned/{self.session_id}_transcoded.mp4"
        output_path = f"./cleaning/cleaned/{self.session_id}_cut.mp4"
        
        # Alinear y cortar
        metadata = self.timestamp_aligner.align_and_cut(
            clean_script,
            transcription,
            video_path,
            output_path
        )
        
        self._log(f"Corte completado: {metadata['total_duration_sec']:.2f}s en {metadata['segments_count']} segmentos")
    
    async def _stage_07_smart_crop(self):
        """Etapa 7: Smart crop a 9:16"""
        self._log("Aplicando smart crop 9:16...")
        
        input_path = f"./cleaning/cleaned/{self.session_id}_cut.mp4"
        output_path = f"./animation/composed/{self.session_id}_cropped.mp4"
        
        metadata = self.video_processor.smart_crop_9_16(
            input_path,
            output_path
        )
        
        self._log(f"Crop completado: {metadata['output_resolution']}, caras detectadas: {metadata['faces_detected']}")
    
    async def _stage_08_plan_anim(self):
        """Etapa 8: Plan de animaciones con IA"""
        self._log("Generando plan de animaciones con IA...")
        
        # Cargar guion limpio
        script_path = f"./cleaning/cleaned/{self.session_id}_script.txt"
        with open(script_path, 'r', encoding='utf-8') as f:
            clean_script = f.read()
        
        # Cargar prompt
        prompt_path = Path("prompts/animation_plan.md")
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        else:
            system_prompt = "Genera un plan detallado de animaciones para este vídeo."
        
        user_prompt = f"""
Guion del vídeo:
{clean_script}

Genera un plan de animaciones en formato JSON:
[
    {{"start": 0.0, "end": 5.0, "type": "text", "content": "Texto", "effect": "fade_in"}},
    ...
]
""".strip()
        
        # Llamar a IA
        animation_plan = await asyncio.to_thread(
            lambda: self.llm_client.chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
                json_mode=True
            )
        )
        
        # Guardar plan
        plan_path = f"./animation/plans/{self.session_id}_plan.json"
        with open(plan_path, 'w', encoding='utf-8') as f:
            json.dump(animation_plan, f, indent=2)
        
        self._log(f"Plan de animación: {len(animation_plan)} elementos")
    
    async def _stage_09_anim_segment(self):
        """Etapa 9: Animación segmentada (sesión fresca por segmento)"""
        self._log("Generando assets de animación...")
        
        plan_path = f"./animation/plans/{self.session_id}_plan.json"
        output_dir = f"./animation/segments/{self.session_id}"
        
        # Contexto del vídeo
        context = {
            "title": f"Clip {self.session_id}",
            "style": "dinámico, moderno",
            "target_duration": f"{self.config.video.output_duration_min}-{self.config.video.output_duration_max}s"
        }
        
        # Ejecutar animaciones
        asset_paths = await self.animation_executor.execute_all(
            plan_path,
            context,
            output_dir
        )
        
        self._log(f"Assets generados: {len(asset_paths)}")
    
    async def _stage_10_composicion(self):
        """Etapa 10: Composición final"""
        self._log("Componiendo vídeo final...")
        
        # Por ahora, simplemente copiar el vídeo cropeado
        # En una implementación completa, aquí se ensamblarían:
        # - Vídeo cropeado
        # - Assets de animación
        # - Subtítulos karaoke
        # - Música con ducking
        
        input_path = f"./animation/composed/{self.session_id}_cropped.mp4"
        output_path = self._get_output_path()
        
        # Copiar archivo (en implementación real, hacer composición)
        import shutil
        shutil.copy(input_path, output_path)
        
        # Quemar subtítulos
        trans_path = f"./cleaning/transcriptions/{self.session_id}.json"
        with open(trans_path, 'r', encoding='utf-8') as f:
            transcription = json.load(f)
        
        words_with_timing = transcription.get('words', [])
        
        # Solo quemar subtítulos de los segmentos cortados
        # (implementación simplificada)
        
        self._log(f"Vídeo final generado: {output_path}")
    
    async def _stage_11_validacion(self):
        """Etapa 11: Validación y upload opcional"""
        self._log("Validando vídeo final...")
        
        output_path = self._get_output_path()
        
        # Validar duración
        try:
            duration = self.video_processor.validate_duration(output_path)
            self._log(f"Duración válida: {duration:.2f}s")
        except VideoDurationError as e:
            self._log(f"Advertencia: {e}")
        
        # Obtener metadatos finales
        info = self.video_processor.get_video_info(output_path)
        
        self._log(f"Output: {info['width']}x{info['height']}, {info['duration']:.2f}s, {info['file_size'] / 1024 / 1024:.2f}MB")
        
        # Upload opcional a YouTube
        if self.config.youtube.upload_enabled:
            self._log("Iniciando subida a YouTube...")
            
            result = self.youtube_uploader.upload(
                output_path,
                title=f"VIDEOAI Clip {self.session_id}",
                description="Generado automáticamente con VIDEOAI"
            )
            
            if result.get("success"):
                self._log("Subida a YouTube iniciada")
            else:
                self._log(f"Upload: {result.get('message', 'Fallido')}")
        else:
            self._log("Upload a YouTube deshabilitado")
    
    def request_cancel(self):
        """Solicita cancelación del pipeline"""
        self._cancel_requested = True
        self._log("Cancelación solicitada")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del pipeline"""
        return {
            "session_id": self.session_id,
            "current_stage": self.current_stage,
            "total_stages": len(self.stages),
            "stages": [s.to_dict() for s in self.stages],
            "logs": self.logs[-50:],  # Últimos 50 logs
            "progress": sum(s.progress for s in self.stages) // len(self.stages) if self.stages else 0
        }
