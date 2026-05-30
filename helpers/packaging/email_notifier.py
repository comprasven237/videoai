"""
VIDEOAI - Notificador por Email
Envía guiones, ideas y notificaciones al creador vía email
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Envía notificaciones automáticas al creador con:
    - Guiones generados
    - Ideas de contenido
    - Alertas de completación
    - Reportes de análisis
    """
    
    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        sender_email: str = "",
        sender_password: str = ""
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.is_configured = bool(sender_email and sender_password)
    
    def send_script_email(
        self,
        recipient: str,
        script_data: Dict[str, Any],
        video_title: str
    ) -> Dict[str, Any]:
        """
        Envía un guion generado por email.
        
        Args:
            recipient: Email del destinatario
            script_data: Datos del guion
            video_title: Título del vídeo
        
        Returns:
            Resultado del envío
        """
        if not self.is_configured:
            return {"success": False, "error": "Email no configurado"}
        
        subject = f"📝 Guion listo: {video_title}"
        
        # Construir cuerpo del email
        body = self._format_script_email(script_data, video_title)
        
        return self._send_email(recipient, subject, body)
    
    def send_ideas_email(
        self,
        recipient: str,
        ideas: List[Dict[str, Any]],
        competitor_analysis: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Envía ideas de contenido basadas en análisis de competidores.
        
        Args:
            recipient: Email del destinatario
            ideas: Lista de ideas generadas
            competitor_analysis: Análisis de competidores opcional
        
        Returns:
            Resultado del envío
        """
        if not self.is_configured:
            return {"success": False, "error": "Email no configurado"}
        
        subject = "💡 Ideas de contenido basadas en tendencias"
        
        body = "🎯 IDEAS DE CONTENIDO GENERADAS\n\n"
        
        if competitor_analysis:
            body += f"📊 Basado en análisis de {competitor_analysis.get('channels_analyzed', 0)} canales\n\n"
        
        for i, idea in enumerate(ideas, 1):
            body += f"{i}. {idea.get('title', 'Sin título')}\n"
            body += f"   Duración: {idea.get('duration', 'N/A')}\n"
            body += f"   Hook: {idea.get('hook', 'N/A')}\n\n"
        
        body += "\n---\nVIDEOAI - Generación automática de contenido"
        
        return self._send_email(recipient, subject, body)
    
    def send_completion_notification(
        self,
        recipient: str,
        session_id: str,
        output_path: str,
        success: bool
    ) -> Dict[str, Any]:
        """
        Notifica completación del pipeline.
        
        Args:
            recipient: Email del destinatario
            session_id: ID de sesión
            output_path: Ruta del vídeo generado
            success: Si el proceso fue exitoso
        
        Returns:
            Resultado del envío
        """
        if not self.is_configured:
            return {"success": False, "error": "Email no configurado"}
        
        status = "✅ COMPLETADO" if success else "❌ FALLIDO"
        subject = f"{status} - Vídeo {session_id}"
        
        body = f"""
🎬 PROCESAMIENTO DE VÍDEO {status}

Sesión: {session_id}
Estado: {'Exitoso' if success else 'Fallido'}
"""
        
        if success:
            body += f"\nRuta del archivo: {output_path}\n"
            body += "\n¡Tu vídeo está listo para publicar!\n"
        else:
            body += "\nRevisa los logs para más detalles.\n"
        
        body += "\n---\nVIDEOAI"
        
        return self._send_email(recipient, subject, body)
    
    def _format_script_email(self, script_data: Dict, title: str) -> str:
        """Formatea el guion para envío por email"""
        body = f"""
📝 GUION GENERADO: {title}

⏱️ Duración objetivo: {script_data.get('target_duration_sec', 0)}s
📱 Formato: {script_data.get('format', 'viral_short')}

═══════════════════════════
ESTRUCTURA DEL GUION
═══════════════════════════

"""
        for section in script_data.get("structure", []):
            body += f"📌 {section['name'].upper()}\n"
            body += f"   Duración: {section.get('duration_sec', 0)}s\n"
            body += f"   Contenido: {section.get('content', '')}\n\n"
        
        if script_data.get("notes"):
            body += "\n📝 NOTAS:\n"
            for note in script_data["notes"]:
                body += f"• {note}\n"
        
        body += "\n---\nVIDEOAI - Generación automática de guiones"
        
        return body
    
    def _send_email(
        self,
        recipient: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Envía email usando SMTP"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = recipient
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            
            text = msg.as_string()
            server.sendmail(self.sender_email, recipient, text)
            server.quit()
            
            logger.info(f"Email enviado a {recipient}: {subject}")
            
            return {"success": True, "message": "Email enviado correctamente"}
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return {"success": False, "error": str(e)}
    
    def configure(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str
    ):
        """Configura credenciales SMTP"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.is_configured = True
        logger.info(f"Email configurado: {sender_email}")
