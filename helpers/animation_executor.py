"""
VIDEOAI - Ejecutor de Animaciones Segmentadas
Procesa cada segmento en una sesión LLM FRESCA para evitar degradación de contexto
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from config import Config, config as global_config
from helpers.llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


@dataclass
class AnimationSegment:
    """Representa un segmento de animación individual"""
    start: float  # segundos
    end: float  # segundos
    type: str  # "text", "zoom", "highlight", "emoji", etc.
    content: str  # texto o descripción del efecto
    effect: str  # tipo de efecto visual


class AnimationExecutor:
    """
    Ejecuta el plan de animaciones procesando cada segmento
    en una sesión LLM fresca para mantener calidad consistente.
    
    PATRÓN CLAVE: Cada segmento <15s se procesa con contexto limpio
    para evitar degradación por acumulación de tokens.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el ejecutor de animaciones.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or global_config
        self.animation_config = self.config.animation
        self.llm_client = UnifiedLLMClient(config)
    
    def load_plan(self, plan_path: str) -> List[AnimationSegment]:
        """
        Carga el plan de animaciones desde JSON.
        
        Args:
            plan_path: Ruta al animation_plan.json
        
        Returns:
            Lista de AnimationSegment
        """
        with open(plan_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        segments = []
        for item in data:
            segment = AnimationSegment(
                start=float(item.get("start", 0)),
                end=float(item.get("end", 0)),
                type=item.get("type", "text"),
                content=item.get("content", item.get("text", "")),
                effect=item.get("effect", "none")
            )
            segments.append(segment)
        
        logger.info(f"Plan de animación cargado: {len(segments)} segmentos")
        
        return segments
    
    async def execute_all(
        self,
        plan_path: str,
        video_context: Dict[str, Any],
        output_dir: str
    ) -> List[str]:
        """
        Ejecuta todas las animaciones del plan con concurrencia controlada.
        
        Args:
            plan_path: Ruta al animation_plan.json
            video_context: Contexto del vídeo (título, tema, estilo)
            output_dir: Directorio para guardar assets generados
        
        Returns:
            Lista de rutas a assets generados
        """
        segments = self.load_plan(plan_path)
        
        # Crear directorio de output específico para este vídeo
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(self.animation_config.max_concurrent_segments)
        
        # Crear tasks para cada segmento
        tasks = []
        for i, segment in enumerate(segments):
            task = self._execute_segment_with_semaphore(
                segment=segment,
                segment_id=i,
                context=video_context,
                output_dir=output_dir,
                semaphore=semaphore
            )
            tasks.append(task)
        
        # Ejecutar todas concurrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filtrar resultados exitosos
        asset_paths = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Segmento {i} falló: {result}")
            elif result:
                asset_paths.append(result)
        
        logger.info(f"Animaciones completadas: {len(asset_paths)}/{len(segments)} assets")
        
        return asset_paths
    
    async def _execute_segment_with_semaphore(
        self,
        segment: AnimationSegment,
        segment_id: int,
        context: Dict[str, Any],
        output_dir: str,
        semaphore: asyncio.Semaphore
    ) -> Optional[str]:
        """
        Ejecuta un segmento con semáforo para control de concurrencia.
        
        Args:
            segment: Segmento a ejecutar
            segment_id: ID único del segmento
            context: Contexto del vídeo
            output_dir: Directorio de output
            semaphore: Semáforo de concurrencia
        
        Returns:
            Ruta al asset generado o None si falla
        """
        async with semaphore:
            return await self._execute_segment_async(
                segment, segment_id, context, output_dir
            )
    
    async def _execute_segment_async(
        self,
        segment: AnimationSegment,
        segment_id: int,
        context: Dict[str, Any],
        output_dir: str
    ) -> Optional[str]:
        """
        Ejecuta un segmento individual en sesión LLM FRESCA.
        
        CRÍTICO: Cada llamada es independiente, sin historial acumulado.
        
        Args:
            segment: Segmento a ejecutar
            segment_id: ID del segmento
            context: Contexto del vídeo
            output_dir: Directorio de output
        
        Returns:
            Ruta al asset generado o None
        """
        logger.debug(f"Ejecutando segmento {segment_id}: {segment.type} ({segment.start}s - {segment.end}s)")
        
        try:
            # Construir prompt específico para este segmento (<500 tokens)
            prompt = self._build_segment_prompt(segment, context, segment_id)
            
            # Sistema específico para generación de assets
            system_prompt = self._load_system_prompt("animation_segment")
            
            # LLAMADA LLM EN SESIÓN FRESCA - sin historial previo
            response = await asyncio.to_thread(
                lambda: self.llm_client.chat(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_mode=True,
                    temperature=0.7
                )
            )
            
            # Parsear respuesta
            if isinstance(response, dict):
                # Generar asset basado en la respuesta
                asset_path = await self._generate_asset(
                    segment=segment,
                    llm_response=response,
                    segment_id=segment_id,
                    output_dir=output_dir
                )
                
                logger.info(f"Segmento {segment_id} completado: {asset_path}")
                return asset_path
            else:
                logger.warning(f"Segmento {segment_id}: respuesta no JSON")
                return None
                
        except Exception as e:
            logger.error(f"Error en segmento {segment_id}: {e}")
            return None
    
    def _build_segment_prompt(
        self,
        segment: AnimationSegment,
        context: Dict[str, Any],
        segment_id: int
    ) -> str:
        """
        Construye prompt específico para un segmento (<500 tokens).
        
        Args:
            segment: Segmento actual
            context: Contexto del vídeo
            segment_id: ID del segmento
        
        Returns:
            Prompt para el LLM
        """
        duration = segment.end - segment.start
        
        prompt = f"""
CONTEXTO DEL VÍDEO:
- Título/Tema: {context.get('title', 'N/A')}
- Estilo visual: {context.get('style', 'dinámico, moderno')}
- Duración objetivo del clip: {context.get('target_duration', '30-90s')}

SEGMENTO {segment_id}:
- Tipo: {segment.type}
- Duración: {duration:.2f} segundos
- Timestamp: {segment.start}s a {segment.end}s
- Contenido/Texto: {segment.content}
- Efecto solicitado: {segment.effect}

INSTRUCCIONES:
Genera los parámetros exactos para crear este elemento visual.
Responde SOLO con JSON en este formato:
{{
    "element_type": "text" | "shape" | "emoji" | "sticker",
    "content": "...",
    "position": {{"x": 0-100, "y": 0-100}},
    "font_size": 24-72,
    "color": "#RRGGBB",
    "animation": "fade_in" | "pop" | "slide" | "none",
    "duration_frames": <número>
}}
""".strip()
        
        return prompt
    
    def _load_system_prompt(self, prompt_name: str) -> str:
        """
        Carga un system prompt desde la carpeta prompts/.
        
        Args:
            prompt_name: Nombre del prompt (sin extensión)
        
        Returns:
            Contenido del prompt
        """
        prompt_path = Path(f"prompts/{prompt_name}.md")
        
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        
        # Fallback genérico
        return """
Eres un asistente especializado en generar parámetros para elementos visuales de vídeo.
Tu trabajo es convertir descripciones de animaciones en especificaciones técnicas precisas.
Responde SIEMPRE en formato JSON válido, sin texto adicional.
""".strip()
    
    async def _generate_asset(
        self,
        segment: AnimationSegment,
        llm_response: Dict[str, Any],
        segment_id: int,
        output_dir: str
    ) -> str:
        """
        Genera el asset visual basado en la respuesta del LLM.
        
        Args:
            segment: Segmento original
            llm_response: Respuesta del LLM con parámetros
            segment_id: ID del segmento
            output_dir: Directorio de output
        
        Returns:
            Ruta al asset generado
        """
        from PIL import Image, ImageDraw, ImageFont
        
        # Parámetros de la respuesta
        element_type = llm_response.get("element_type", "text")
        content = llm_response.get("content", segment.content)
        position = llm_response.get("position", {"x": 50, "y": 50})
        font_size = llm_response.get("font_size", 48)
        color = llm_response.get("color", "#FFFFFF")
        
        # Dimensiones del canvas (vertical 9:16)
        width = self.config.video.width   # 1080
        height = self.config.video.height # 1920
        
        # Crear imagen transparente
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuente
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # Dibujar según tipo de elemento
        if element_type == "text":
            # Obtener bounding box del texto
            bbox = draw.textbbox((0, 0), content, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calcular posición (porcentajes a píxeles)
            x = int(position.get("x", 50) * width / 100) - text_width // 2
            y = int(position.get("y", 50) * height / 100) - text_height // 2
            
            # Sombra
            shadow_offset = 4
            draw.text(
                (x + shadow_offset, y + shadow_offset),
                content,
                font=font,
                fill=(0, 0, 0, 180)
            )
            
            # Texto principal
            draw.text((x, y), content, font=font, fill=self._hex_to_rgba(color))
        
        elif element_type == "shape":
            # Dibujar forma geométrica simple
            shape_size = font_size * 2
            x = int(position.get("x", 50) * width / 100) - shape_size // 2
            y = int(position.get("y", 50) * height / 100) - shape_size // 2
            
            draw.ellipse(
                [x, y, x + shape_size, y + shape_size],
                fill=self._hex_to_rgba(color)
            )
        
        # Guardar asset
        asset_filename = f"segment_{segment_id:03d}_{segment.type}.png"
        asset_path = Path(output_dir) / asset_filename
        
        img.save(asset_path, 'PNG')
        
        return str(asset_path)
    
    def _hex_to_rgba(self, hex_color: str) -> tuple:
        """
        Convierte color hexadecimal a tupla RGBA.
        
        Args:
            hex_color: Color en formato #RRGGBB
        
        Returns:
            Tupla (R, G, B, A)
        """
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b, 255)
        elif len(hex_color) == 8:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
            return (r, g, b, a)
        
        return (255, 255, 255, 255)  # Blanco por defecto
    
    def split_long_segments(
        self,
        segments: List[AnimationSegment],
        max_duration: float = 15.0
    ) -> List[AnimationSegment]:
        """
        Divide segmentos largos en múltiples segmentos más cortos.
        
        CRÍTICO PARA EVITAR DEGRADACIÓN DE CONTEXTO:
        Ningún segmento debe exceder max_duration segundos.
        
        Args:
            segments: Lista original de segmentos
            max_duration: Duración máxima por segmento
        
        Returns:
            Lista con segmentos divididos
        """
        result = []
        
        for segment in segments:
            duration = segment.end - segment.start
            
            if duration <= max_duration:
                # No necesita división
                result.append(segment)
            else:
                # Dividir en múltiple segmentos
                num_splits = int(duration // max_duration) + 1
                split_duration = duration / num_splits
                
                for i in range(num_splits):
                    split_start = segment.start + (i * split_duration)
                    split_end = min(split_start + split_duration, segment.end)
                    
                    split_segment = AnimationSegment(
                        start=split_start,
                        end=split_end,
                        type=segment.type,
                        content=f"{segment.content} ({i+1}/{num_splits})",
                        effect=segment.effect
                    )
                    result.append(split_segment)
        
        logger.info(f"Segmentación: {len(segments)} -> {len(result)} segmentos")
        
        return result
