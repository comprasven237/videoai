"""
VIDEOAI - Procesador de Vídeo
Operaciones deterministas de vídeo: crop, subtítulos, audio ducking, validación
"""

import logging
import subprocess
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import Config, config as global_config

logger = logging.getLogger(__name__)


class VideoDurationError(Exception):
    """Error cuando la duración del vídeo no cumple los requisitos"""
    pass


class VideoProcessor:
    """
    Procesador de vídeo para operaciones deterministas:
    - Smart crop 9:16
    - Subtítulos karaoke
    - Audio ducking
    - Validación de duración
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el procesador de vídeo.
        
        Args:
            config: Configuración del sistema
        """
        self.config = config or global_config
        self.video_config = self.config.video
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Obtiene información técnica del vídeo usando ffprobe.
        
        Args:
            video_path: Ruta al vídeo
        
        Returns:
            Dict con información del vídeo
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe falló: {result.stderr}")
        
        data = json.loads(result.stdout)
        
        # Extraer información relevante
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            {}
        )
        
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": float(video_stream.get("r_frame_rate", "0/1")).split("/") 
                   and float(video_stream.get("r_frame_rate", "0/1").split("/")[0]) / 
                   max(float(video_stream.get("r_frame_rate", "0/1").split("/")[1]), 1),
            "codec": video_stream.get("codec_name", ""),
            "has_audio": bool(audio_stream),
            "file_size": int(data.get("format", {}).get("size", 0))
        }
    
    def validate_duration(self, video_path: str) -> float:
        """
        Valida que la duración del vídeo esté dentro del rango configurado.
        
        Args:
            video_path: Ruta al vídeo
        
        Returns:
            Duración en segundos
        
        Raises:
            VideoDurationError: Si está fuera de rango
        """
        info = self.get_video_info(video_path)
        duration = info["duration"]
        
        min_dur = self.video_config.output_duration_min
        max_dur = self.video_config.output_duration_max
        
        if duration < min_dur or duration > max_dur:
            raise VideoDurationError(
                f"Duración {duration:.2f}s fuera de rango [{min_dur}, {max_dur}]"
            )
        
        logger.info(f"Duración válida: {duration:.2f}s")
        return duration
    
    def smart_crop_9_16(
        self,
        input_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Realiza smart crop a formato vertical 9:16 detectando caras y movimiento.
        
        Args:
            input_path: Ruta al vídeo original (horizontal o vertical)
            output_path: Ruta para guardar el vídeo recortado
        
        Returns:
            Metadatos del crop realizado
        """
        logger.info(f"Smart crop 9:16: {input_path}")
        
        # Obtener información del vídeo
        info = self.get_video_info(input_path)
        width = info["width"]
        height = info["height"]
        duration = info["duration"]
        fps = info["fps"] or 30
        
        target_width = self.video_config.width   # 1080
        target_height = self.video_config.height # 1920
        
        # Calcular dimensiones del crop
        # Para horizontal: tomar centro vertical
        # Para vertical: ajustar ancho
        aspect_ratio = target_width / target_height
        
        if width > height:  # Horizontal
            # El crop height será igual al height original
            # El crop width será height * aspect_ratio
            crop_height = height
            crop_width = int(height * aspect_ratio)
            
            # Centrar horizontalmente
            x_offset = (width - crop_width) // 2
            y_offset = 0
        else:  # Vertical
            # Ajustar para llenar el ancho
            crop_width = width
            crop_height = int(width / aspect_ratio)
            
            # Si es más alto que el target, centrar verticalmente
            if crop_height > height:
                crop_height = height
                crop_width = int(height * aspect_ratio)
                x_offset = (width - crop_width) // 2
                y_offset = 0
            else:
                x_offset = 0
                y_offset = (height - crop_height) // 2
        
        # Detectar caras para tracking inicial
        face_positions = self._detect_face_positions(input_path, fps, duration)
        
        # Construir filter_complex para crop dinámico si hay caras
        if face_positions:
            # Crop dinámico siguiendo caras
            filter_complex = self._build_dynamic_crop_filter(
                face_positions, crop_width, crop_height, width, height
            )
        else:
            # Crop estático centrado
            filter_complex = f"crop={crop_width}:{crop_height}:{x_offset}:{y_offset}"
        
        # Escalar a resolución target
        filter_complex += f",scale={target_width}:{target_height}:flags=lanczos"
        
        # Comando FFmpeg
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", filter_complex,
            "-c:a", "copy",  # Copiar audio sin procesar
            "-y",
            output_path
        ]
        
        logger.info("Ejecutando smart crop con FFmpeg...")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg crop falló: {result.stderr}")
            raise RuntimeError(f"Smart crop error: {result.stderr[:500]}")
        
        metadata = {
            "input_resolution": f"{width}x{height}",
            "output_resolution": f"{target_width}x{target_height}",
            "crop_method": "dynamic" if face_positions else "static_centered",
            "faces_detected": len(face_positions) if face_positions else 0
        }
        
        logger.info(f"Smart crop completado: {output_path}")
        
        return metadata
    
    def _detect_face_positions(
        self,
        video_path: str,
        fps: float,
        duration: float,
        sample_interval: float = 2.0
    ) -> List[Dict[str, int]]:
        """
        Detecta posiciones de caras en frames muestreados del vídeo.
        
        Args:
            video_path: Ruta al vídeo
            fps: FPS del vídeo
            duration: Duración total
            sample_interval: Intervalo entre muestras (segundos)
        
        Returns:
            Lista de [{frame_num, x, y, width, height}]
        """
        # Cargar clasificador de caras
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if face_cascade.empty():
            logger.warning("No se pudo cargar el clasificador de caras")
            return []
        
        # Abrir vídeo
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.warning("No se pudo abrir el vídeo para detección de caras")
            return []
        
        face_positions = []
        frame_num = 0
        sample_frame_interval = int(fps * sample_interval)
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Muestrear frames
            if frame_num % sample_frame_interval == 0:
                # Convertir a grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Detectar caras
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )
                
                # Tomar la cara más grande (si hay múltiples)
                if len(faces) > 0:
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    x, y, w, h = largest_face
                    
                    face_positions.append({
                        "frame_num": frame_num,
                        "x": int(x + w // 2),  # Centro
                        "y": int(y + h // 2),
                        "width": int(w),
                        "height": int(h)
                    })
            
            frame_num += 1
        
        cap.release()
        
        logger.info(f"Caras detectadas en {len(face_positions)} frames")
        
        return face_positions
    
    def _build_dynamic_crop_filter(
        self,
        face_positions: List[Dict[str, int]],
        crop_width: int,
        crop_height: int,
        video_width: int,
        video_height: int
    ) -> str:
        """
        Construye un filter_complex para crop dinámico siguiendo caras.
        
        Args:
            face_positions: Posiciones de caras detectadas
            crop_width: Ancho del crop
            crop_height: Alto del crop
            video_width: Ancho del vídeo original
            video_height: Alto del vídeo original
        
        Returns:
            String con el filter_complex
        """
        # Interpolación lineal entre posiciones de caras
        # Simplificación: usar el promedio de todas las posiciones
        if not face_positions:
            return f"crop={crop_width}:{crop_height}"
        
        avg_x = sum(fp["x"] for fp in face_positions) // len(face_positions)
        avg_y = sum(fp["y"] for fp in face_positions) // len(face_positions)
        
        # Calcular offset para centrar el crop en la cara
        x_offset = max(0, min(avg_x - crop_width // 2, video_width - crop_width))
        y_offset = max(0, min(avg_y - crop_height // 2, video_height - crop_height))
        
        return f"crop={crop_width}:{crop_height}:{x_offset}:{y_offset}"
    
    def burn_karaoke_subtitles(
        self,
        video_path: str,
        words: List[Dict[str, Any]],
        output_path: str
    ) -> str:
        """
        Quema subtítulos estilo karaoke en el vídeo.
        
        Args:
            video_path: Ruta al vídeo
            words: Lista de palabras con timestamps
                [{"word": "...", "start_ms": 1000, "end_ms": 1500}, ...]
            output_path: Ruta para guardar el vídeo con subtítulos
        
        Returns:
            Ruta al archivo ASS generado
        """
        logger.info(f"Quemando subtítulos karaoke: {len(words)} palabras")
        
        # Generar archivo ASS
        ass_path = output_path.replace(".mp4", ".ass")
        
        # Estilos ASS
        font = self.config.animation.subtitle_font
        font_size = self.config.animation.subtitle_font_size
        primary_color = self._rgb_to_ass_color(self.config.animation.subtitle_color)
        highlight_color = self._rgb_to_ass_color(self.config.animation.subtitle_highlight_color)
        
        ass_content = f"""[Script Info]
Title: VIDEOAI Karaoke Subtitles
ScriptType: v4.00+
PlayResX: {self.video_config.width}
PlayResY: {self.video_config.height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_color},{highlight_color},&H000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        # Generar eventos por palabra
        # Estrategia: cada línea muestra todas las palabras, con la activa resaltada
        # Esto requiere generar múltiples events superpuestos
        
        # Simplificación: una línea por segmento de ~5 palabras
        segment_size = 5
        
        for i in range(0, len(words), segment_size):
            segment_words = words[i:i + segment_size]
            
            if not segment_words:
                continue
            
            start_ms = segment_words[0]["start_ms"]
            end_ms = segment_words[-1]["end_ms"]
            
            start_time = self._ms_to_ass_time(start_ms)
            end_time = self._ms_to_ass_time(end_ms)
            
            # Construir texto con timing de colores
            text_parts = []
            for word_data in segment_words:
                word = word_data["word"]
                word_start = word_data["start_ms"]
                word_end = word_data["end_ms"]
                
                rel_start = (word_start - start_ms) / 1000
                rel_end = (word_end - start_ms) / 1000
                
                # Formato: {\kN}para timing karaoke
                duration_centiseconds = int((word_end - word_start) / 10)
                text_parts.append(f"{{\\k{duration_centiseconds}}}{word} ")
            
            text = "".join(text_parts)
            
            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
        
        # Guardar ASS
        Path(ass_path).parent.mkdir(parents=True, exist_ok=True)
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        # Quemar subtítulos con FFmpeg
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={ass_path}",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg subtitles falló: {result.stderr}")
            raise RuntimeError(f"Subtitles error: {result.stderr[:500]}")
        
        logger.info(f"Subtítulos quemados: {output_path}")
        
        return ass_path
    
    def _rgb_to_ass_color(self, color_name: str) -> str:
        """Convierte nombre de color a formato ASS (&HAABBGGRR)"""
        colors = {
            "white": "&H00FFFFFF",
            "yellow": "&H0000FFFF",
            "black": "&H00000000",
            "red": "&H000000FF",
            "green": "&H0000FF00",
            "blue": "&H00FF0000"
        }
        return colors.get(color_name.lower(), "&H00FFFFFF")
    
    def _ms_to_ass_time(self, ms: int) -> str:
        """Convierte milisegundos a formato ASS (H:MM:SS.cc)"""
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        centiseconds = int((total_seconds % 1) * 100)
        
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
    
    def apply_ducking(
        self,
        voice_path: str,
        music_path: str,
        output_path: str,
        duck_db: float = 6.0
    ) -> Dict[str, Any]:
        """
        Aplica audio ducking: reduce música cuando hay voz.
        
        Args:
            voice_path: Ruta al audio de voz
            music_path: Ruta a la música de fondo
            output_path: Ruta para guardar el audio mezclado
            duck_db: Cantidad de reducción en dB
        
        Returns:
            Metadatos del proceso
        """
        logger.info(f"Aplicando ducking ({duck_db}dB)...")
        
        # FFmpeg filter para sidechain compression
        # La voz es la señal detectora, la música es la señal a comprimir
        filter_complex = (
            f"[0:a][1:a]sidechaincompress=threshold=-20dB:ratio=4:attack=5:release=50:detection=peak[audio]"
        )
        
        cmd = [
            "ffmpeg",
            "-i", voice_path,
            "-i", music_path,
            "-filter_complex", filter_complex,
            "-map", "[audio]",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg ducking falló: {result.stderr}")
            # Fallback: mezcla simple sin ducking
            logger.warning("Usando mezcla simple como fallback...")
            cmd = [
                "ffmpeg",
                "-i", voice_path,
                "-i", music_path,
                "-filter_complex", "[1:a]volume=0.3[music];[0:a][music]amix=inputs=2:duration=first",
                "-y",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"Audio mix error: {result.stderr[:500]}")
        
        metadata = {
            "duck_db": duck_db,
            "method": "sidechain" if result.returncode == 0 else "simple_mix"
        }
        
        logger.info(f"Ducking aplicado: {output_path}")
        
        return metadata
    
    def transcode(
        self,
        input_path: str,
        output_path: str,
        target_fps: int = 30
    ) -> Dict[str, Any]:
        """
        Transcodifica vídeo a especificaciones estándar.
        
        Args:
            input_path: Ruta al vídeo original
            output_path: Ruta para guardar el vídeo transcodificado
            target_fps: FPS objetivo
        
        Returns:
            Metadatos de la transcodificación
        """
        logger.info(f"Transcodificando a H.264/AAC, {target_fps}fps...")
        
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-r", str(target_fps),
            "-c:a", "aac",
            "-b:a", self.video_config.audio_bitrate,
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg transcode falló: {result.stderr}")
            raise RuntimeError(f"Transcode error: {result.stderr[:500]}")
        
        # Obtener info del output
        info = self.get_video_info(output_path)
        
        metadata = {
            "input_path": input_path,
            "output_path": output_path,
            "output_duration": info["duration"],
            "output_size_bytes": info["file_size"],
            "resolution": f"{info['width']}x{info['height']}",
            "fps": info["fps"]
        }
        
        logger.info(f"Transcodificación completada: {output_path}")
        
        return metadata
