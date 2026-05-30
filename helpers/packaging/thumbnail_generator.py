"""
VIDEOAI - Generador de Thumbnails
Crea thumbnails atractivas con texto, expresiones faciales y elementos virales
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    """
    Genera thumbnails optimizadas para CTR usando:
    - Expresiones faciales exageradas
    - Texto grande y contrastante
    - Colores vibrantes
    - Composición rule of thirds
    """
    
    def __init__(self):
        self.thumbnail_templates = {
            "shock": {
                "expression": "sorpresa/shock",
                "text_position": "top",
                "colors": ["red", "yellow"],
                "emoji": "😱"
            },
            "curiosity": {
                "expression": "curiosidad/intriga",
                "text_position": "bottom",
                "colors": ["blue", "white"],
                "emoji": "🤔"
            },
            "success": {
                "expression": "éxito/felicidad",
                "text_position": "center",
                "colors": ["green", "gold"],
                "emoji": "🎉"
            }
        }
    
    def generate_thumbnail_plan(
        self,
        video_title: str,
        style: str = "shock",
        include_face: bool = True,
        text_overlay: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera un plan para crear thumbnail.
        
        Args:
            video_title: Título del vídeo
            style: Estilo emocional (shock, curiosity, success)
            include_face: Si incluir rostro con expresión
            text_overlay: Texto personalizado para overlay
        
        Returns:
            Plan detallado para generación de thumbnail
        """
        template = self.thumbnail_templates.get(style, self.thumbnail_templates["shock"])
        
        # Generar texto corto si no se proporciona
        if not text_overlay:
            text_overlay = self._extract_hook_words(video_title)
        
        plan = {
            "style": style,
            "template": template,
            "title": video_title,
            "text_overlay": text_overlay,
            "include_face": include_face,
            "composition": {
                "rule_of_thirds": True,
                "face_position": "left" if include_face else None,
                "text_position": template["text_position"],
                "background_blur": True
            },
            "colors": {
                "primary": template["colors"][0],
                "accent": template["colors"][1],
                "text_color": "white" if style == "shock" else "black"
            },
            "elements": []
        }
        
        if include_face:
            plan["elements"].append({
                "type": "face_expression",
                "expression": template["expression"],
                "enhancement": "eyes_enhanced"
            })
        
        plan["elements"].append({
            "type": "text_overlay",
            "content": text_overlay,
            "font_size": "large",
            "effect": "outline_shadow"
        })
        
        return plan
    
    def _extract_hook_words(self, title: str, max_words: int = 4) -> str:
        """Extrae las palabras más impactantes del título"""
        hook_words = [
            "increíble", "impactante", "secreto", "nunca", "gratis",
            "fácil", "rápido", "mejor", "peor", "error", "truco"
        ]
        
        words = title.lower().split()
        found_hooks = [w for w in words if w in hook_words]
        
        if found_hooks:
            return " ".join(found_hooks[:max_words]).upper()
        
        # Fallback: primeras palabras
        return " ".join(words[:max_words]).upper()
    
    def generate_batch(
        self,
        titles: List[str],
        styles: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Genera múltiples variantes de thumbnails para A/B testing.
        
        Args:
            titles: Lista de títulos
            styles: Estilos a usar (default: todos)
        
        Returns:
            Lista de planes de thumbnails
        """
        if styles is None:
            styles = list(self.thumbnail_templates.keys())
        
        variants = []
        for title in titles:
            for style in styles:
                plan = self.generate_thumbnail_plan(title, style)
                plan["variant_id"] = f"{titles.index(title)}_{style}"
                variants.append(plan)
        
        return variants
    
    def export_for_generation(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exporta el plan en formato compatible con herramientas de generación.
        
        Args:
            plan: Plan de thumbnail
        
        Returns:
            Dict listo para enviar a API de generación de imágenes
        """
        prompt_parts = []
        
        if plan.get("include_face"):
            expr = plan["template"]["expression"]
            prompt_parts.append(f"persona con expresión de {expr}, primer plano")
        
        prompt_parts.append(f"fondo desenfocado, colores {plan['colors']['primary']} y {plan['colors']['accent']}")
        prompt_parts.append(f"texto grande: '{plan['text_overlay']}'")
        prompt_parts.append("estilo YouTube thumbnail, alta calidad, 1280x720")
        
        return {
            "prompt": ", ".join(prompt_parts),
            "negative_prompt": "texto borroso, baja calidad, caras deformes",
            "width": 1280,
            "height": 720,
            "steps": 30,
            "cfg_scale": 7
        }
