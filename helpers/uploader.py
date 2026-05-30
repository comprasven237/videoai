"""
VIDEOAI - Uploader para YouTube (opcional)
Sube vídeos automáticamente usando Selenium
"""

import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path

from config import Config, config as global_config

logger = logging.getLogger(__name__)


class YouTubeUploader:
    """
    Sube vídeos a YouTube usando Selenium.
    Nota: Requiere autenticación manual previa del navegador.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el uploader.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or global_config
        self.upload_enabled = self.config.youtube.upload_enabled
    
    def upload(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: list = None,
        privacy_status: str = "private"
    ) -> Dict[str, Any]:
        """
        Sube un vídeo a YouTube.
        
        Args:
            video_path: Ruta al vídeo
            title: Título del vídeo
            description: Descripción
            tags: Lista de tags
            privacy_status: "private", "unlisted", o "public"
        
        Returns:
            Dict con resultado de la subida
        
        Raises:
            RuntimeError: Si la subida falla
        """
        if not self.upload_enabled:
            logger.info("Upload a YouTube deshabilitado en configuración")
            return {
                "success": False,
                "reason": "upload_disabled",
                "message": "La subida automática está deshabilitada"
            }
        
        logger.info(f"Iniciando subida a YouTube: {video_path}")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError as e:
            logger.error(f"Selenium no disponible: {e}")
            return {
                "success": False,
                "reason": "selenium_not_installed",
                "message": "Selenium no está instalado. Instala: pip install selenium webdriver-manager"
            }
        
        # Configurar driver
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        # Para producción: usar perfil existente con sesión guardada
        # options.add_argument("--user-data-dir=/path/to/chrome/profile")
        
        driver = None
        
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            
            # Ir a YouTube Studio
            driver.get("https://studio.youtube.com/upload")
            
            # Esperar a que cargue el selector de archivos
            wait = WebDriverWait(driver, 30)
            
            # Buscar input de archivo
            file_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            
            # Subir archivo
            file_input.send_keys(str(Path(video_path).absolute()))
            
            # Esperar procesamiento inicial
            time.sleep(5)
            
            # Completar detalles
            # Título
            title_input = driver.find_element(By.CSS_SELECTOR, '#textbox')
            title_input.clear()
            title_input.send_keys(title)
            
            # Descripción (si existe campo)
            if description:
                try:
                    desc_inputs = driver.find_elements(By.CSS_SELECTOR, '#textbox')
                    if len(desc_inputs) > 1:
                        desc_inputs[1].clear()
                        desc_inputs[1].send_keys(description)
                except:
                    pass
            
            # Visibilidad
            privacy_map = {
                "private": 0,
                "unlisted": 1,
                "public": 2
            }
            
            # Navegar a configuración de visibilidad
            # (esto puede variar según UI de YouTube)
            
            logger.info("Subida iniciada. Monitorear progreso manualmente.")
            
            return {
                "success": True,
                "message": "Subida iniciada. Completa los detalles manualmente en YouTube Studio.",
                "video_path": video_path
            }
            
        except Exception as e:
            logger.error(f"Error en subida a YouTube: {e}")
            return {
                "success": False,
                "reason": "upload_error",
                "message": str(e)
            }
        
        finally:
            if driver:
                # No cerrar inmediatamente para permitir completar manualmente
                # driver.quit()
                pass
    
    def upload_api(self, video_path: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alternativa: subida usando YouTube Data API v3.
        Requiere credentials.json y autenticación OAuth2.
        
        Args:
            video_path: Ruta al vídeo
            metadata: Metadatos del vídeo
        
        Returns:
            Dict con resultado de la subida
        """
        logger.warning(
            "YouTube API upload no implementado completamente. "
            "Requiere configurar OAuth2 y descargar credentials.json."
        )
        
        return {
            "success": False,
            "reason": "not_implemented",
            "message": "YouTube API upload requiere configuración adicional de OAuth2"
        }
