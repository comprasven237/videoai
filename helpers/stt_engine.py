"""
VIDEOAI - Motor de Speech-to-Text usando faster-whisper
Transcripción local con timestamps a nivel de palabra
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from config import Config, config as global_config

logger = logging.getLogger(__name__)


class STTEngine:
    """
    Wrapper para faster-whisper que proporciona transcripción
    con timestamps a nivel de palabra.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el motor STT.
        
        Args:
            config: Configuración del sistema. Si None, usa la configuración global.
        """
        self.config = config or global_config
        self.model_size = self.config.stt.model_size
        self._model = None
    
    def _load_model(self):
        """Carga el modelo whisper en memoria (lazy loading)"""
        if self._model is None:
            logger.info(f"Cargando modelo Whisper: {self.model_size}")
            from faster_whisper import WhisperModel
            
            # Determinar dispositivo automáticamente
            device = self.config.stt.device
            if device == "auto":
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            
            compute_type = self.config.stt.compute_type
            if compute_type == "default":
                compute_type = "float16" if device == "cuda" else "int8"
            
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type
            )
            logger.info(f"Modelo Whisper cargado en {device}")
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe un archivo de audio/vídeo con timestamps por palabra.
        
        Args:
            audio_path: Ruta al archivo de audio o vídeo
            language: Código de idioma (ej: "es", "en"). Si None, auto-detecta.
        
        Returns:
            Dict con:
            {
                "text": str,  # Texto completo
                "segments": [  # Segmentos con timestamps
                    {
                        "start": float,  # segundos
                        "end": float,
                        "text": str,
                        "confidence": float
                    }
                ],
                "words": [  # Timestamps a nivel de palabra
                    {
                        "word": str,
                        "start_ms": int,
                        "end_ms": int,
                        "confidence": float
                    }
                ]
            }
        """
        self._load_model()
        
        logger.info(f"Transcribiendo: {audio_path}")
        
        # Ejecutar transcripción
        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,  # CRÍTICO: timestamps por palabra
            vad_filter=True  # Filtrar silencios
        )
        
        # Procesar resultados
        full_text = []
        all_segments = []
        all_words = []
        
        for segment in segments:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": segment.avg_logprob if hasattr(segment, 'avg_logprob') else 0.0
            }
            all_segments.append(segment_dict)
            full_text.append(segment.text)
            
            # Extraer palabras con timestamps
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_dict = {
                        "word": word.word,
                        "start_ms": int(word.start * 1000),
                        "end_ms": int(word.end * 1000),
                        "confidence": word.probability if hasattr(word, 'probability') else 0.0
                    }
                    all_words.append(word_dict)
        
        result = {
            "text": "".join(full_text),
            "segments": all_segments,
            "words": all_words,
            "language": info.language if info else "unknown",
            "duration": info.duration if info else 0.0
        }
        
        logger.info(
            f"Transcripción completada: {len(all_words)} palabras, "
            f"idioma: {result['language']}"
        )
        
        return result
    
    def transcribe_and_save(
        self,
        audio_path: str,
        output_json_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe y guarda el resultado en JSON.
        
        Args:
            audio_path: Ruta al archivo de audio/vídeo
            output_json_path: Ruta donde guardar el JSON
            language: Código de idioma opcional
        
        Returns:
            Resultado de la transcripción
        """
        result = self.transcribe(audio_path, language)
        
        # Guardar JSON
        output_path = Path(output_json_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Transcripción guardada en: {output_json_path}")
        
        return result
