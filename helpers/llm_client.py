"""
VIDEOAI - Cliente LLM Unificado y Agnóstico
Cliente HTTP puro usando requests para comunicarse con CUALQUIER servidor LLM
compatible con el formato /v1/chat/completions

NO usa SDKs propietarios. Solo requests HTTP estándar.
"""

import json
import time
import logging
from typing import Optional, Union, Dict, Any, List
from pathlib import Path

import requests

from config import Config, config as global_config

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    """Error de conexión con el endpoint LLM"""
    pass


class LLMResponseError(Exception):
    """Error en la respuesta del LLM"""
    pass


class UnifiedLLMClient:
    """
    Cliente HTTP unificado para comunicarse con cualquier endpoint LLM.
    
    Soporta:
    - Servidores locales (Ollama, LM Studio, vLLM, etc.)
    - APIs externas (OpenAI, Anthropic, etc.)
    
    REQUISITO: El endpoint debe ser compatible con el formato:
    POST {endpoint}/chat/completions
    Body: {"model": "...", "messages": [...]}
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Inicializa el cliente LLM.
        
        Args:
            config: Configuración del sistema. Si None, usa la configuración global.
        """
        self.config = config or global_config
        self.llm_config = self.config.llm
        
        # Validar configuración básica
        if not self.llm_config.endpoint:
            logger.warning("LLM endpoint no configurado")
        
        # Normalizar endpoint (asegurar que termine sin /)
        self.endpoint = self.llm_config.endpoint.rstrip("/")
        
        # Construir URL completa para chat completions
        # El usuario puede poner http://localhost:1234 o http://localhost:1234/v1
        # Necesitamos asegurarnos de llamar a /chat/completions
        if self.endpoint.endswith("/v1"):
            self.chat_url = f"{self.endpoint}/chat/completions"
        elif "/v1" not in self.endpoint:
            # Asumir que necesita /v1 agregado
            self.chat_url = f"{self.endpoint}/v1/chat/completions"
        else:
            self.chat_url = f"{self.endpoint}/chat/completions"        
        logger.info(f"LLM Client inicializado - Endpoint: {self.chat_url}")
    
    def _build_headers(self) -> Dict[str, str]:
        """
        Construye los headers HTTP para la request.
        
        Returns:
            Diccionario con headers apropiados según el modo configurado.
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        # Agregar Authorization solo si es modo API y hay API key
        # En modo local, generalmente no se requiere auth, pero si el usuario
        # puso una key, la usamos (algunos servidores locales pueden requerirla)
        if self.llm_config.api_key:
            headers["Authorization"] = f"Bearer {self.llm_config.api_key}"
        
        return headers
    
    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Construye el payload JSON para la request.
        
        Args:
            messages: Lista de mensajes [{role, content}]
            temperature: Temperatura para la generación (default: config)
            json_mode: Si True, solicita respuesta en formato JSON
        
        Returns:
            Diccionario con el payload completo
        """
        payload = {
            "model": self.llm_config.model,
            "messages": messages,
            "temperature": temperature or self.llm_config.temperature
        }
        
        # Solicitar formato JSON si es necesario
        if json_mode:
            # Algunos modelos soportan response_format
            payload["response_format"] = {"type": "json_object"}
        
        return payload
    
    def _make_request(
        self,
        payload: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> requests.Response:
        """
        Realiza la request HTTP al endpoint.
        
        Args:
            payload: Payload JSON para enviar
            timeout: Timeout en segundos (default: config)
        
        Returns:
            Response de requests
        
        Raises:
            LLMConnectionError: Si falla la conexión
        """
        timeout = timeout or self.llm_config.timeout
        
        try:
            response = requests.post(
                self.chat_url,
                headers=self._build_headers(),
                json=payload,
                timeout=timeout
            )
            return response
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(
                f"No se pudo conectar al endpoint {self.chat_url}. "
                f"Verifica que tu servidor LLM esté corriendo y la URL sea correcta."
            ) from e
        except requests.exceptions.Timeout as e:
            raise LLMConnectionError(
                f"Timeout al conectar con {self.chat_url} después de {timeout}s. "
                f"El modelo puede estar procesando una request muy larga."
            ) from e
        except requests.exceptions.RequestException as e:
            raise LLMConnectionError(
                f"Error de red al conectar con {self.chat_url}: {str(e)}"
            ) from e
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: Optional[float] = None,
        max_retries: Optional[int] = None
    ) -> Union[str, Dict]:
        """
        Envía un mensaje al LLM y obtiene la respuesta.
        
        Args:
            prompt: Mensaje del usuario
            system_prompt: Prompt de sistema opcional
            json_mode: Si True, espera y parsea respuesta JSON
            temperature: Temperatura para la generación
            max_retries: Número máximo de reintentos (default: config)
        
        Returns:
            str si json_mode=False, dict si json_mode=True
        
        Raises:
            LLMConnectionError: Si falla la conexión
            LLMResponseError: Si la respuesta no es válida
        """
        max_retries = max_retries or self.llm_config.max_retries
        
        # Construir mensajes
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Intentar con reintentos exponenciales
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                logger.debug(f"LLM request (intento {attempt + 1}/{max_retries + 1})")
                
                payload = self._build_payload(
                    messages=messages,
                    temperature=temperature,
                    json_mode=json_mode
                )
                
                response = self._make_request(payload)
                
                # Verificar status code
                if response.status_code != 200:
                    error_msg = response.text[:500] if response.text else "Sin detalles"
                    raise LLMResponseError(
                        f"Endpoint retornó status {response.status_code}: {error_msg}"
                    )
                
                # Parsear respuesta
                data = response.json()
                
                # Extraer contenido de la respuesta
                # Formato estándar OpenAI: choices[0].message.content
                if "choices" not in data or len(data["choices"]) == 0:
                    raise LLMResponseError(
                        "Respuesta inválida: no contiene 'choices'"
                    )
                
                content = data["choices"][0]["message"]["content"]
                
                # Log sin exponer API keys
                logger.info(f"LLM response recibida ({len(content)} caracteres)")
                
                # Retornar según modo
                if json_mode:
                    return self._parse_json_response(content)
                else:
                    return content.strip()
                
            except (LLMConnectionError, LLMResponseError) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = (2 ** attempt)  # Backoff exponencial: 1s, 2s, 4s...
                    logger.warning(f"Intento {attempt + 1} fallido, reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    break
        
        # Todos los reintentos fallaron
        raise last_error
    
    def _parse_json_response(self, content: str) -> Dict:
        """
        Parsea una respuesta JSON del LLM con fallbacks robustos.
        
        Args:
            content: Contenido crudo de la respuesta
        
        Returns:
            Diccionario parseado
        
        Raises:
            LLMResponseError: Si no se puede parsear JSON
        """
        # Intento 1: Parseo directo
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Intento 2: Buscar bloque JSON en el contenido
        # El LLM a veces agrega texto antes/después del JSON
        import re
        json_pattern = r'\{[^{}]*\}|\{(?:[^{}]|(?R))*\}'
        matches = re.findall(r'\{.*?\}', content, re.DOTALL)
        
        for match in reversed(matches):  # Probar desde el último (más probable)
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Intento 3: Buscar entre ```json y ```
        json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Todo falló
        raise LLMResponseError(
            f"No se pudo parsear JSON de la respuesta. Contenido: {content[:200]}..."
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica la conexión con el endpoint LLM.
        
        Returns:
            Dict con {"ok": bool, "message": str}
        """
        if not self.llm_config.endpoint:
            return {
                "ok": False,
                "message": "Endpoint no configurado. Configura tu servidor LLM en el Dashboard."
            }
        
        if not self.llm_config.model:
            return {
                "ok": False,
                "message": "Modelo no especificado. Ingresa el nombre del modelo en la configuración."
            }
        
        # Request mínimo de prueba
        test_messages = [
            {"role": "user", "content": "Responde solo: OK"}
        ]
        
        try:
            payload = self._build_payload(test_messages, temperature=0.1)
            response = self._make_request(payload)
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return {
                        "ok": True,
                        "message": f"Conexión exitosa. Modelo: {self.llm_config.model}"
                    }
                else:
                    return {
                        "ok": False,
                        "message": "Respuesta inválida del servidor (sin choices)"
                    }
            else:
                return {
                    "ok": False,
                    "message": f"Status {response.status_code}: {response.text[:200]}"
                }
                
        except LLMConnectionError as e:
            return {
                "ok": False,
                "message": str(e)
            }
        except Exception as e:
            return {
                "ok": False,
                "message": f"Error inesperado: {str(e)}"
            }
    
    def get_mode_display(self) -> str:
        """
        Retorna string descriptivo del modo configurado.
        
        Returns:
            String legible para mostrar en UI
        """
        if self.llm_config.mode == "local":
            return f"Local ({self.llm_config.endpoint})"
        elif self.llm_config.mode == "api":
            # Ocultar parte de la API key por seguridad
            key_display = "****" + self.llm_config.api_key[-4:] if self.llm_config.api_key else "Sin key"
            return f"API ({key_display})"
        else:
            return "No configurado"
