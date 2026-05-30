#!/usr/bin/env python3
"""
VIDEOAI Launcher - Aplicación de escritorio con botón de inicio
Compatible con Windows, macOS y Linux
"""

import os
import sys
import subprocess
import webbrowser
import socket
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except ImportError:
    TK_AVAILABLE = False

# Configuración
APP_NAME = "VIDEOAI"
VERSION = "1.0.0"
PORT = 5555
HOST = "localhost"


def check_port_available(port):
    """Verifica si el puerto está disponible"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False


def find_python():
    """Encuentra el ejecutable de Python"""
    if sys.platform == 'win32':
        possible_paths = [
            sys.executable,
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', '*', 'python.exe'),
            os.path.join('C:', 'Python*', 'python.exe'),
        ]
    else:
        possible_paths = [sys.executable, '/usr/bin/python3', '/opt/homebrew/bin/python3']
    
    for path in possible_paths:
        if os.path.exists(path.replace('*', '')):
            return path
    
    # Fallback al actual
    return sys.executable or 'python'


def start_server():
    """Inicia el servidor VIDEOAI"""
    script_dir = Path(__file__).parent.absolute()
    main_py = script_dir / 'main.py'
    
    if not main_py.exists():
        if TK_AVAILABLE:
            messagebox.showerror("Error", f"No se encontró main.py en {script_dir}")
        else:
            print(f"ERROR: No se encontró main.py en {script_dir}")
        return None
    
    python_exe = find_python()
    
    # Configurar variables de entorno
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # Iniciar proceso
    process = subprocess.Popen(
        [python_exe, str(main_py)],
        cwd=str(script_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    return process


class VideoAILauncher:
    """Clase principal del launcher con interfaz gráfica"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Centrar ventana
        self.center_window()
        
        # Configurar estilos
        self.setup_styles()
        
        # Variables de estado
        self.server_process = None
        self.server_running = False
        
        # Crear interfaz
        self.create_widgets()
        
        # Verificar estado inicial
        self.check_initial_state()
    
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.root.update_idletasks()
        width = 500
        height = 400
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_styles(self):
        """Configura los estilos de la aplicación"""
        style = ttk.Style()
        
        # Colores
        bg_color = '#0f0f0f'
        card_color = '#1a1a1a'
        accent_color = '#00d4aa'
        text_color = '#ffffff'
        
        self.root.configure(bg=bg_color)
        
        # Configurar fuentes
        style.configure('Title.TLabel', 
                       font=('Helvetica', 24, 'bold'),
                       background=bg_color,
                       foreground=text_color)
        
        style.configure('Subtitle.TLabel',
                       font=('Helvetica', 12),
                       background=bg_color,
                       foreground='#888888')
        
        style.configure('Status.TLabel',
                       font=('Helvetica', 10),
                       background=bg_color,
                       foreground=accent_color)
        
        style.configure('Accent.TButton',
                       font=('Helvetica', 16, 'bold'),
                       background=accent_color,
                       foreground='#000000')
    
    def create_widgets(self):
        """Crea todos los widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo/Título
        title_label = ttk.Label(
            main_frame, 
            text=f"🎬 {APP_NAME}",
            style='Title.TLabel'
        )
        title_label.pack(pady=(20, 5))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Producción de Vídeo Automatizada con IA",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Frame del botón principal
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        # Botón de inicio gigante
        self.start_button = tk.Button(
            button_frame,
            text="🚀 INICIAR VIDEOAI",
            font=('Helvetica', 18, 'bold'),
            bg='#00d4aa',
            fg='#000000',
            activebackground='#00b894',
            activeforeground='#000000',
            relief=tk.FLAT,
            cursor='hand2',
            command=self.toggle_server,
            width=20,
            height=2
        )
        self.start_button.pack(pady=10)
        
        # Estado del servidor
        self.status_label = ttk.Label(
            main_frame,
            text="Estado: ⚫ Detenido",
            style='Status.TLabel'
        )
        self.status_label.pack(pady=10)
        
        # Información del puerto
        self.port_label = ttk.Label(
            main_frame,
            text=f"Puerto: {PORT}",
            style='Subtitle.TLabel'
        )
        self.port_label.pack(pady=5)
        
        # URL del dashboard
        self.url_label = ttk.Label(
            main_frame,
            text="",
            style='Subtitle.TLabel',
            foreground='#00d4aa'
        )
        self.url_label.pack(pady=5)
        
        # Frame de acciones
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(pady=20, fill=tk.X)
        
        # Botón abrir dashboard
        self.open_button = tk.Button(
            actions_frame,
            text="🌐 Abrir Dashboard",
            font=('Helvetica', 11),
            bg='#1a1a1a',
            fg='#ffffff',
            activebackground='#2a2a2a',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            command=self.open_dashboard,
            state=tk.DISABLED
        )
        self.open_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Botón salir
        exit_button = tk.Button(
            actions_frame,
            text="❌ Salir",
            font=('Helvetica', 11),
            bg='#1a1a1a',
            fg='#ffffff',
            activebackground='#ff4444',
            activeforeground='#ffffff',
            relief=tk.FLAT,
            cursor='hand2',
            command=self.exit_app
        )
        exit_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Área de logs
        logs_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        logs_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        self.logs_text = tk.Text(
            logs_frame,
            height=6,
            bg='#1a1a1a',
            fg='#ffffff',
            insertbackground='white',
            font=('Consolas', 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.logs_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar para logs
        scrollbar = ttk.Scrollbar(logs_frame, orient=tk.VERTICAL, command=self.logs_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.logs_text.config(yscrollcommand=scrollbar.set)
    
    def log_message(self, message):
        """Agrega un mensaje al área de logs"""
        self.logs_text.config(state=tk.NORMAL)
        timestamp = subprocess.check_output(['date', '+%H:%M:%S'], text=True).strip() if sys.platform != 'win32' else ''
        self.logs_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.logs_text.see(tk.END)
        self.logs_text.config(state=tk.DISABLED)
    
    def check_initial_state(self):
        """Verifica el estado inicial de la aplicación"""
        if not check_port_available(PORT):
            self.log_message(f"⚠️ El puerto {PORT} ya está en uso")
            self.server_running = True
            self.update_ui_for_running()
        else:
            self.log_message("✅ Listo para iniciar")
    
    def toggle_server(self):
        """Alterna entre iniciar/detener el servidor"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()
    
    def start_server(self):
        """Inicia el servidor VIDEOAI"""
        self.log_message("🔄 Iniciando servidor...")
        self.start_button.config(state=tk.DISABLED, text="⏳ Iniciando...")
        
        # Ejecutar en hilo separado
        import threading
        thread = threading.Thread(target=self._start_server_thread, daemon=True)
        thread.start()
    
    def _start_server_thread(self):
        """Hilo para iniciar el servidor"""
        try:
            self.server_process = start_server()
            
            if self.server_process:
                self.server_running = True
                self.root.after(0, self.update_ui_for_running)
                self.root.after(0, lambda: self.log_message("✅ Servidor iniciado correctamente"))
                
                # Monitorear salida del proceso
                self.monitor_process()
            else:
                self.root.after(0, lambda: self.log_message("❌ Error al iniciar el servidor"))
                self.root.after(0, self.reset_ui)
        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"❌ Error: {str(e)}"))
            self.root.after(0, self.reset_ui)
    
    def monitor_process(self):
        """Monitorea el proceso del servidor"""
        if self.server_process and self.server_process.poll() is not None:
            self.server_running = False
            self.log_message("⚠️ El servidor se ha detenido")
            self.reset_ui()
        elif self.server_running:
            self.root.after(1000, self.monitor_process)
    
    def stop_server(self):
        """Detiene el servidor"""
        self.log_message("🛑 Deteniendo servidor...")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            
            self.server_process = None
        
        self.server_running = False
        self.update_ui_for_stopped()
        self.log_message("✅ Servidor detenido")
    
    def update_ui_for_running(self):
        """Actualiza la UI cuando el servidor está corriendo"""
        self.start_button.config(
            state=tk.NORMAL,
            text="⏹️ DETENER",
            bg='#ff6b6b',
            activebackground='#ee5a5a'
        )
        self.status_label.config(text="Estado: 🟢 En ejecución")
        self.open_button.config(state=tk.NORMAL)
        self.url_label.config(text=f"👉 http://localhost:{PORT}")
    
    def update_ui_for_stopped(self):
        """Actualiza la UI cuando el servidor está detenido"""
        self.start_button.config(
            state=tk.NORMAL,
            text="🚀 INICIAR VIDEOAI",
            bg='#00d4aa',
            activebackground='#00b894'
        )
        self.status_label.config(text="Estado: ⚫ Detenido")
        self.open_button.config(state=tk.DISABLED)
        self.url_label.config(text="")
    
    def reset_ui(self):
        """Resetea la UI al estado inicial"""
        self.update_ui_for_stopped()
        self.start_button.config(state=tk.NORMAL)
    
    def open_dashboard(self):
        """Abre el dashboard en el navegador"""
        url = f"http://localhost:{PORT}"
        webbrowser.open(url)
        self.log_message(f"🌐 Abriendo dashboard en {url}")
    
    def exit_app(self):
        """Sale de la aplicación"""
        if self.server_running:
            if TK_AVAILABLE:
                if messagebox.askyesno("Confirmar", "¿El servidor está corriendo. ¿Deseas detenerlo y salir?"):
                    self.stop_server()
                    self.root.quit()
            else:
                self.stop_server()
                sys.exit(0)
        else:
            self.root.quit()


def run_cli_mode():
    """Ejecuta en modo CLI (sin GUI)"""
    print(f"\n{'='*50}")
    print(f"🎬 {APP_NAME} v{VERSION}")
    print(f"{'='*50}\n")
    
    if not check_port_available(PORT):
        print(f"⚠️ El puerto {PORT} ya está en uso")
        print(f"👉 Dashboard disponible en: http://localhost:{PORT}\n")
    else:
        print("🚀 Iniciando servidor VIDEOAI...")
        print(f"📍 Puerto: {PORT}")
        print(f"🌐 Dashboard: http://localhost:{PORT}")
        print(f"\nPresiona Ctrl+C para detener el servidor\n")
        
        process = start_server()
        
        if process:
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Deteniendo servidor...")
                process.terminate()
                print("✅ Servidor detenido. ¡Hasta luego!")


def main():
    """Función principal"""
    # Determinar si usar GUI o CLI
    use_gui = TK_AVAILABLE and len(sys.argv) == 1
    
    if use_gui:
        # Modo GUI
        root = tk.Tk()
        app = VideoAILauncher(root)
        
        # Manejar cierre de ventana
        root.protocol("WM_DELETE_WINDOW", app.exit_app)
        
        root.mainloop()
    else:
        # Modo CLI
        if not TK_AVAILABLE:
            print("ℹ️ Tkinter no disponible, ejecutando en modo consola...\n")
        run_cli_mode()


if __name__ == '__main__':
    main()
