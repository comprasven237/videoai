"""
VIDEOAI - Alineador de Timestamps a Nivel de Palabra
Compara el guion limpio (IA) con la transcripción original (STT)
y calcula cortes exactos en milisegundos para precisión frame-perfect
"""

import logging
import difflib
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class TimestampAligner:
    """
    Alinea el guion limpio generado por la IA con los timestamps
    originales de la transcripción STT para calcular cortes precisos.
    """
    
    def __init__(self):
        """Inicializa el alineador"""
        pass
    
    def _tokenize_words(self, text: str) -> List[str]:
        """
        Tokeniza texto a nivel de palabra normalizado.
        
        Args:
            text: Texto a tokenizar
        
        Returns:
            Lista de palabras normalizadas (minúsculas, sin puntuación)
        """
        import re
        # Convertir a minúsculas y extraer solo palabras
        words = re.findall(r'\b[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+\b', text.lower())
        return words
    
    def _normalize_word(self, word: str) -> str:
        """Normaliza una palabra para comparación"""
        import re
        return re.sub(r'[^\w]', '', word).lower()
    
    def align(
        self,
        clean_script: str,
        original_transcription: Dict[str, Any]
    ) -> List[Dict[str, int]]:
        """
        Alinea el guion limpio con los timestamps originales.
        
        Args:
            clean_script: Guion limpio generado por la IA (texto plano)
            original_transcription: Resultado de STT con timestamps por palabra
                {
                    "words": [
                        {"word": "...", "start_ms": 1000, "end_ms": 1500},
                        ...
                    ]
                }
        
        Returns:
            Lista de segmentos [{start_ms, end_ms}] que deben conservarse
        """
        logger.info("Alineando guion limpio con transcripción original...")
        
        # Tokenizar ambos textos
        clean_words = self._tokenize_words(clean_script)
        original_words = original_transcription.get("words", [])
        
        if not original_words:
            raise ValueError("Transcripción original no contiene palabras con timestamps")
        
        if not clean_words:
            raise ValueError("Guion limpio está vacío")
        
        logger.debug(f"Guion limpio: {len(clean_words)} palabras")
        logger.debug(f"Transcripción original: {len(original_words)} palabras")
        
        # Crear secuencias para alineación difusa
        clean_normalized = [self._normalize_word(w) for w in clean_words]
        original_normalized = [self._normalize_word(w["word"]) for w in original_words]
        
        # Alineación usando SequenceMatcher
        matcher = difflib.SequenceMatcher(None, clean_normalized, original_normalized)
        
        # Encontrar bloques coincidentes
        matching_blocks = matcher.get_matching_blocks()
        
        # Convertir bloques a segmentos de tiempo
        segments = []
        
        for block in matching_blocks:
            # block: (a_idx, b_idx, size)
            # a_idx: índice en clean_normalized
            # b_idx: índice en original_normalized  
            # size: tamaño del match
            
            if block.size == 0:
                continue
            
            # Obtener palabras originales en este bloque
            start_orig_idx = block.b
            end_orig_idx = block.b + block.size
            
            if start_orig_idx >= len(original_words):
                continue
            if end_orig_idx > len(original_words):
                end_orig_idx = len(original_words)
            
            # Calcular timestamps
            start_ms = original_words[start_orig_idx]["start_ms"]
            end_ms = original_words[end_orig_idx - 1]["end_ms"]
            
            segments.append({
                "start_ms": start_ms,
                "end_ms": end_ms,
                "word_count": block.size
            })
        
        # Fusionar segmentos adyacentes (gap < 2 segundos)
        merged_segments = self._merge_adjacent_segments(segments, gap_threshold_ms=2000)
        
        logger.info(f"Alineación completada: {len(merged_segments)} segmentos")
        
        return merged_segments
    
    def _merge_adjacent_segments(
        self,
        segments: List[Dict[str, int]],
        gap_threshold_ms: int = 2000
    ) -> List[Dict[str, int]]:
        """
        Fusiona segmentos adyacentes si el gap es menor al threshold.
        
        Args:
            segments: Lista de segmentos
            gap_threshold_ms: Gap máximo para fusionar (ms)
        
        Returns:
            Lista de segmentos fusionados
        """
        if not segments:
            return []
        
        # Ordenar por tiempo de inicio
        sorted_segments = sorted(segments, key=lambda s: s["start_ms"])
        
        merged = [sorted_segments[0].copy()]
        
        for current in sorted_segments[1:]:
            last = merged[-1]
            gap = current["start_ms"] - last["end_ms"]
            
            if gap <= gap_threshold_ms:
                # Fusionar
                last["end_ms"] = max(last["end_ms"], current["end_ms"])
                last["word_count"] += current.get("word_count", 0)
            else:
                # Nuevo segmento
                merged.append(current.copy())
        
        return merged
    
    def align_and_cut(
        self,
        clean_script: str,
        original_transcription: Dict[str, Any],
        video_path: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Alinea y realiza el corte físico del vídeo.
        
        Args:
            clean_script: Guion limpio de la IA
            original_transcription: Transcripción STT con timestamps
            video_path: Ruta al vídeo original
            output_path: Ruta donde guardar el vídeo cortado
        
        Returns:
            Metadatos del corte
        """
        # Obtener segmentos alineados
        segments = self.align(clean_script, original_transcription)
        
        if not segments:
            raise ValueError("No se encontraron segmentos válidos para cortar")
        
        # Calcular duración total
        total_duration_ms = sum(s["end_ms"] - s["start_ms"] for s in segments)
        total_duration_sec = total_duration_ms / 1000
        
        logger.info(f"Duración total después del corte: {total_duration_sec:.2f}s")
        
        # Generar comando FFmpeg
        # Usar filter_complex para concatenar segmentos sin re-encode cuando sea posible
        import subprocess
        
        # Construir filtros para cada segmento
        filter_parts = []
        for i, seg in enumerate(segments):
            start_sec = seg["start_ms"] / 1000
            duration_sec = (seg["end_ms"] - seg["start_ms"]) / 1000
            filter_parts.append(
                f"[0:v]trim=start={start_sec}:duration={duration_sec},setpts=PTS-STARTPTS[v{i}];"
                f"[0:a]atrim=start={start_sec}:duration={duration_sec},asetpts=PTS-STARTPTS[a{i}]"
            )
        
        # Concatenar todos los segmentos
        num_segments = len(segments)
        concat_inputs_v = "".join(f"[v{i}]" for i in range(num_segments))
        concat_inputs_a = "".join(f"[a{i}]" for i in range(num_segments))
        filter_parts.append(
            f"{concat_inputs_v}concat=n={num_segments}:v=1:a=0[outv];"
            f"{concat_inputs_a}concat=n={num_segments}:v=0:a=1[outa]"
        )
        
        filter_complex = ";".join(filter_parts)
        
        # Comando FFmpeg
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-y",  # Sobrescribir
            output_path
        ]
        
        logger.info(f"Ejecutando FFmpeg para corte físico...")
        
        # Ejecutar
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg falló: {result.stderr}")
            raise RuntimeError(f"FFmpeg error: {result.stderr[:500]}")
        
        # Verificar output
        output_file = Path(output_path)
        if not output_file.exists():
            raise RuntimeError("FFmpeg no generó el archivo de output")
        
        metadata = {
            "segments_count": len(segments),
            "total_duration_sec": total_duration_sec,
            "segments": segments,
            "output_path": str(output_path),
            "output_size_bytes": output_file.stat().st_size
        }
        
        logger.info(f"Corte físico completado: {output_path}")
        
        return metadata
    
    def calculate_highlight_cuts(
        self,
        highlights: List[Dict[str, Any]],
        original_transcription: Dict[str, Any]
    ) -> List[Dict[str, int]]:
        """
        Convierte highlights de la IA (con timestamps aproximados)
        a cortes precisos basados en los timestamps del STT.
        
        Args:
            highlights: Lista de highlights de la IA
                [{"start": float, "end": float, ...}, ...]
            original_transcription: Transcripción STT
        
        Returns:
            Lista de segmentos precisos [{start_ms, end_ms}]
        """
        original_words = original_transcription.get("words", [])
        
        if not original_words:
            raise ValueError("Transcripción sin timestamps")
        
        precise_segments = []
        
        for highlight in highlights:
            start_sec = highlight.get("start", 0)
            end_sec = highlight.get("end", 0)
            
            # Encontrar palabras más cercanas
            start_ms = self._find_nearest_timestamp(original_words, start_sec, "start")
            end_ms = self._find_nearest_timestamp(original_words, end_sec, "end")
            
            if start_ms is not None and end_ms is not None:
                precise_segments.append({
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "reason": highlight.get("reason", ""),
                    "viral_score": highlight.get("viral_score", 0)
                })
        
        return precise_segments
    
    def _find_nearest_timestamp(
        self,
        words: List[Dict[str, Any]],
        target_sec: float,
        mode: str = "start"
    ) -> Optional[int]:
        """
        Encuentra el timestamp más cercano en las palabras originales.
        
        Args:
            words: Lista de palabras con timestamps
            target_sec: Tiempo objetivo en segundos
            mode: "start" o "end"
        
        Returns:
            Timestamp en ms o None
        """
        target_ms = int(target_sec * 1000)
        
        # Búsqueda binaria simple
        best_match = None
        best_diff = float('inf')
        
        for word in words:
            ts = word["start_ms"] if mode == "start" else word["end_ms"]
            diff = abs(ts - target_ms)
            
            if diff < best_diff:
                best_diff = diff
                best_match = ts
        
        return best_match
