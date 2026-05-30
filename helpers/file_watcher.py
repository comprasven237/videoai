"""
VIDEOAI - File Watcher para Watch Folder Pattern
Monitorea la carpeta /cleaning/raw/ y dispara el pipeline automáticamente
"""

import logging
import asyncio
import json
from typing import Callable, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from config import Config, config as global_config

logger = logging.getLogger(__name__)


class VideoFileHandler(FileSystemEventHandler):
    """
    Handler que detecta nuevos vídeos en la watch folder.
    """
    
    def __init__(self, callback: Callable[[str], None], config: Config):
        """
        Inicializa el handler.
        
        Args:
            callback: Función a llamar cuando se detecta un nuevo vídeo
            config: Configuración del sistema
        """
        self.callback = callback
        self.config = config
        self._processed_files: Dict[str, datetime] = {}
    
    def on_created(self, event):
        """
        Se dispara cuando se crea un archivo.
        
        Args:
            event: Evento de filesystem
        """
        if isinstance(event, FileCreatedEvent):
            file_path = event.src_path
            
            # Verificar si es un archivo de vídeo válido
            if self._is_video_file(file_path):
                logger.info(f"Nuevo vídeo detectado: {file_path}")
                
                # Evitar procesar el mismo archivo múltiples veces
                if file_path in self._processed_files:
                    last_processed = self._processed_files[file_path]
                    if (datetime.now() - last_processed).total_seconds() < 60:
                        logger.debug(f"Archivo ya procesado recientemente: {file_path}")
                        return
                
                # Registrar como procesado
                self._processed_files[file_path] = datetime.now()
                
                # Llamar al callback (pipeline)
                try:
                    self.callback(file_path)
                except Exception as e:
                    logger.error(f"Error al procesar {file_path}: {e}")
    
    def _is_video_file(self, file_path: str) -> bool:
        """
        Verifica si el archivo es un vídeo válido.
        
        Args:
            file_path: Ruta al archivo
        
        Returns:
            True si es un vídeo válido
        """
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}
        path = Path(file_path)
        
        # Verificar extensión
        if path.suffix.lower() not in video_extensions:
            return False
        
        # Verificar que no sea archivo temporal (.part, .tmp, etc.)
        if path.suffix.lower() in {'.part', '.tmp', '.crdownload'}:
            return False
        
        # Verificar que el archivo tenga tamaño > 0 (ya existe)
        try:
            if path.stat().st_size == 0:
                return False
        except:
            pass
        
        return True


class FileWatcher:
    """
    Watcher que monitorea la carpeta de entrada de vídeos.
    Implementa el patrón Watch Folder para procesamiento automático.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el file watcher.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or global_config
        self.watch_folder = Path(self.config.paths.watch_folder)
        self.observer: Optional[Observer] = None
        self._callback: Optional[Callable] = None
        self._running = False
    
    def set_callback(self, callback: Callable[[str], None]):
        """
        Establece el callback que se ejecutará cuando se detecte un nuevo vídeo.
        
        Args:
            callback: Función que recibe la ruta del vídeo detectado
        """
        self._callback = callback
        logger.info(f"Callback registrado para watch folder: {self.watch_folder}")
    
    def start(self):
        """
        Inicia el watcher en background.
        """
        if self._running:
            logger.warning("Watcher ya está corriendo")
            return
        
        if not self._callback:
            logger.error("No hay callback registrado. Usa set_callback() primero.")
            return
        
        # Asegurar que la carpeta existe
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        
        # Crear handler y observer
        handler = VideoFileHandler(self._callback, self.config)
        self.observer = Observer()
        self.observer.schedule(handler, str(self.watch_folder), recursive=False)
        
        # Iniciar observer
        self.observer.start()
        self._running = True
        
        logger.info(f"Watcher iniciado en: {self.watch_folder}")
    
    def stop(self):
        """
        Detiene el watcher.
        """
        if self.observer and self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False
            logger.info("Watcher detenido")
    
    def is_running(self) -> bool:
        """
        Verifica si el watcher está corriendo.
        
        Returns:
            True si está activo
        """
        return self._running
    
    def scan_existing(self) -> list:
        """
        Escanea archivos existentes en la watch folder.
        Útil para procesar vídeos que ya estaban antes de iniciar el watcher.
        
        Returns:
            Lista de rutas de vídeos encontrados
        """
        video_files = []
        
        if not self.watch_folder.exists():
            return video_files
        
        for file_path in self.watch_folder.iterdir():
            if file_path.is_file():
                handler = VideoFileHandler(lambda x: None, self.config)
                if handler._is_video_file(str(file_path)):
                    video_files.append(str(file_path))
        
        logger.info(f"Scan completado: {len(video_files)} vídeos existentes")
        
        return video_files
