"""
VIDEOAI - Arquitecto de Guiones
Genera guiones estructurados basados en análisis de competidores y patrones virales
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ScriptArchitect:
    """
    Genera guiones optimizados para viralidad basados en:
    - Patrones de competidores exitosos
    - Estructuras probadas (hook, desarrollo, CTA)
    - Duración objetivo del formato
    """
    
    def __init__(self):
        self.script_templates = {
            "viral_short": {
                "hook_duration": 3,
                "structure": ["hook", "setup", "development", "payoff", "cta"],
                "target_duration_sec": 60
            },
            "youtube_long": {
                "hook_duration": 15,
                "structure": ["hook", "intro", "main_content", "climax", "conclusion", "cta"],
                "target_duration_sec": 480
            }
        }
    
    def generate_script(
        self,
        topic: str,
        format_type: str = "viral_short",
        competitor_insights: Optional[Dict] = None,
        target_audience: str = "general"
    ) -> Dict[str, Any]:
        """
        Genera un guion completo basado en el tema y formato.
        
        Args:
            topic: Tema principal del vídeo
            format_type: 'viral_short' o 'youtube_long'
            competitor_insights: Datos de análisis de competidores
            target_audience: Audiencia objetivo
        
        Returns:
            Guion estructurado con timestamps y secciones
        """
        template = self.script_templates.get(format_type, self.script_templates["viral_short"])
        
        script = {
            "topic": topic,
            "format": format_type,
            "target_duration_sec": template["target_duration_sec"],
            "structure": [],
            "full_text": "",
            "notes": []
        }
        
        # Generar estructura básica
        sections = []
        for section_name in template["structure"]:
            section = {
                "name": section_name,
                "duration_sec": self._estimate_section_duration(section_name, template),
                "content": f"[{section_name.upper()}] - Contenido a desarrollar",
                "hooks": [] if section_name == "hook" else None
            }
            sections.append(section)
        
        script["structure"] = sections
        
        # Agregar insights de competidores si están disponibles
        if competitor_insights:
            script["notes"].append(
                f"Basado en análisis de {competitor_insights.get('total_videos', 0)} vídeos competidores"
            )
        
        return script
    
    def _estimate_section_duration(self, section_name: str, template: Dict) -> int:
        """Estima duración de una sección basada en su importancia"""
        duration_weights = {
            "hook": 0.1,
            "setup": 0.15,
            "development": 0.4,
            "payoff": 0.2,
            "cta": 0.05,
            "intro": 0.1,
            "main_content": 0.5,
            "climax": 0.15,
            "conclusion": 0.1
        }
        
        weight = duration_weights.get(section_name, 0.2)
        return int(template["target_duration_sec"] * weight)
    
    def optimize_for_platform(
        self,
        script: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """
        Optimiza un guion para una plataforma específica.
        
        Args:
            script: Guion base
            platform: 'tiktok', 'youtube_shorts', 'instagram_reels', 'youtube'
        
        Returns:
            Guion optimizado para la plataforma
        """
        platform_specs = {
            "tiktok": {"max_duration": 180, "aspect_ratio": "9:16", "hook_critical": True},
            "youtube_shorts": {"max_duration": 60, "aspect_ratio": "9:16", "hook_critical": True},
            "instagram_reels": {"max_duration": 90, "aspect_ratio": "9:16", "hook_critical": True},
            "youtube": {"max_duration": 720, "aspect_ratio": "16:9", "hook_critical": False}
        }
        
        specs = platform_specs.get(platform, platform_specs["tiktok"])
        script["platform_optimization"] = specs
        
        # Ajustar duración si excede máximo
        if script["target_duration_sec"] > specs["max_duration"]:
            script["target_duration_sec"] = specs["max_duration"]
            script["notes"].append(f"Duración ajustada a {specs['max_duration']}s para {platform}")
        
        return script
    
    def generate_from_transcript(
        self,
        transcript: str,
        target_duration: int = 60
    ) -> Dict[str, Any]:
        """
        Extrae y estructura un guion desde una transcripción existente.
        
        Args:
            transcript: Transcripción completa del contenido
            target_duration: Duración objetivo en segundos
        
        Returns:
            Guion estructurado extraído del transcript
        """
        # Placeholder para extracción inteligente
        return {
            "source": "transcript_extraction",
            "original_length": len(transcript),
            "target_duration_sec": target_duration,
            "extracted_sections": [],
            "full_text": transcript[:1000] + "..." if len(transcript) > 1000 else transcript
        }
