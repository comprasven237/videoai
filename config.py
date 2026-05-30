"""
VIDEOAI - Configuración del Sistema
Carga configuración desde config.yaml y .env usando Pydantic Settings
"""

import os
from typing import Optional, Literal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import yaml


class LLMConfig(BaseSettings):
    """Configuración del cliente LLM (agnóstico)"""
    mode: Literal["", "local", "api"] = ""
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    temperature: float = 0.7
    timeout: int = 60
    max_retries: int = 2
    
    @property
    def is_configured(self) -> bool:
        """Verifica si el LLM está configurado correctamente"""
        return bool(self.mode and self.endpoint and self.model)
    
    @property
    def requires_auth(self) -> bool:
        """Verifica si requiere autenticación"""
        return self.mode == "api" and bool(self.api_key)


class STTConfig(BaseSettings):
    """Configuración de Speech-to-Text"""
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "default"


class VideoConfig(BaseSettings):
    """Configuración de procesamiento de vídeo"""
    output_duration_min: int = 30
    output_duration_max: int = 90
    resolution: str = "1080x1920"
    fps: int = 30
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    video_bitrate: str = "8M"
    audio_loudness: str = "-14 LUFS"
    
    @property
    def width(self) -> int:
        parts = self.resolution.split("x")
        return int(parts[0]) if len(parts) >= 1 else 1080
    
    @property
    def height(self) -> int:
        parts = self.resolution.split("x")
        return int(parts[1]) if len(parts) >= 2 else 1920


class AnimationConfig(BaseSettings):
    """Configuración de animaciones"""
    max_segment_duration: int = 15
    max_concurrent_segments: int = 3
    subtitle_font: str = "Arial"
    subtitle_font_size: int = 48
    subtitle_color: str = "white"
    subtitle_highlight_color: str = "yellow"


class PathsConfig(BaseSettings):
    """Configuración de rutas"""
    watch_folder: str = "./cleaning/raw"
    packaging: str = "./packaging"
    cleaning: str = "./cleaning"
    animation: str = "./animation"
    output: str = "./output"
    assets: str = "./assets"
    logs: str = "./logs"
    state: str = "./state"
    
    def ensure_exists(self):
        """Crea todas las carpetas si no existen"""
        for path in [
            self.watch_folder, self.packaging, 
            f"{self.cleaning}/raw", f"{self.cleaning}/transcriptions", f"{self.cleaning}/cleaned",
            f"{self.animation}/plans", f"{self.animation}/segments", f"{self.animation}/composed",
            self.output, self.assets, self.logs, self.state
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)


class DashboardConfig(BaseSettings):
    """Configuración del Dashboard"""
    port: int = 5555
    host: str = "0.0.0.0"


class YouTubeConfig(BaseSettings):
    """Configuración de YouTube"""
    upload_enabled: bool = False
    privacy_status: str = "private"


class Config(BaseSettings):
    """Configuración principal del sistema VIDEOAI"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Sub-configuraciones
    llm: LLMConfig = Field(default_factory=LLMConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    animation: AnimationConfig = Field(default_factory=AnimationConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    
    # Variables directas del .env (para compatibilidad)
    llm_mode: str = ""
    llm_endpoint: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    stt_model_size: str = "base"
    output_duration_min: int = 30
    output_duration_max: int = 90
    resolution: str = "1080x1920"
    watch_folder: str = "./cleaning/raw"
    youtube_upload_enabled: bool = False
    dashboard_port: int = 5555
    
    def __init__(self, **kwargs):
        # Primero cargar config.yaml
        config_path = Path("config.yaml")
        yaml_config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
        
        # Actualizar con valores del .env
        super().__init__(**kwargs)
        
        # Sincronizar variables del .env con sub-objetos
        self._sync_env_to_objects()
    
    def _sync_env_to_objects(self):
        """Sincroniza variables del .env con los objetos de configuración"""
        if self.llm_mode:
            self.llm.mode = self.llm_mode
        if self.llm_endpoint:
            self.llm.endpoint = self.llm_endpoint
        if self.llm_model:
            self.llm.model = self.llm_model
        if self.llm_api_key:
            self.llm.api_key = self.llm_api_key
        
        if self.stt_model_size:
            self.stt.model_size = self.stt_model_size
        
        if self.output_duration_min:
            self.video.output_duration_min = self.output_duration_min
        if self.output_duration_max:
            self.video.output_duration_max = self.output_duration_max
        
        if self.resolution:
            self.video.resolution = self.resolution
        
        if self.watch_folder:
            self.paths.watch_folder = self.watch_folder
        
        if self.youtube_upload_enabled is not None:
            self.youtube.upload_enabled = self.youtube_upload_enabled
        
        if self.dashboard_port:
            self.dashboard.port = self.dashboard_port
    
    def is_fully_configured(self) -> bool:
        """Verifica si el sistema está completamente configurado"""
        return self.llm.is_configured
    
    def save_to_env(self, data: dict):
        """Guarda configuración en .env"""
        lines = [
            "# VIDEOAI - Configuración generada automáticamente",
            "# No editar manualmente - usar el Dashboard",
            ""
        ]
        
        mapping = {
            "llm_mode": "LLM_MODE",
            "llm_endpoint": "LLM_ENDPOINT",
            "llm_model": "LLM_MODEL",
            "llm_api_key": "LLM_API_KEY",
            "stt_model_size": "STT_MODEL_SIZE",
            "output_duration_min": "OUTPUT_DURATION_MIN",
            "output_duration_max": "OUTPUT_DURATION_MAX",
            "resolution": "RESOLUTION",
            "watch_folder": "WATCH_FOLDER",
            "youtube_upload_enabled": "YOUTUBE_UPLOAD_ENABLED",
            "dashboard_port": "DASHBOARD_PORT"
        }
        
        for key, env_name in mapping.items():
            value = data.get(key, getattr(self, key, ""))
            lines.append(f"{env_name}={value}")
        
        with open(".env", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        # Recargar configuración
        self.__init__()


def get_config() -> Config:
    """Obtiene la configuración global del sistema"""
    config = Config()
    config.paths.ensure_exists()
    return config


# Instancia global
config = get_config()
