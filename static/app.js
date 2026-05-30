/**
 * VIDEOAI - JavaScript del Dashboard
 * Funcionalidades comunes para la interfaz de usuario
 */

// ============================================================================
// WEBSOCKET MANAGER
// ============================================================================

class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.listeners = new Map();
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.url}`;
        
        console.log(`Conectando a WebSocket: ${wsUrl}`);
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('✅ WebSocket conectado');
            this.reconnectAttempts = 0;
            this.emit('open');
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.emit('message', data);
            } catch (e) {
                this.emit('message', event.data);
            }
        };

        this.ws.onerror = (error) => {
            console.error('❌ Error en WebSocket:', error);
            this.emit('error', error);
        };

        this.ws.onclose = () => {
            console.log('🔌 WebSocket desconectado');
            this.emit('close');
            
            // Intentar reconectar
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.pow(2, this.reconnectAttempts) * 1000;
                console.log(`Reintentando en ${delay}ms...`);
                setTimeout(() => this.connect(), delay);
            }
        };
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket no está conectado');
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    emit(event, data) {
        const callbacks = this.listeners.get(event) || [];
        callbacks.forEach(cb => cb(data));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// ============================================================================
// API CLIENT
// ============================================================================

class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async testLLMConnection(config) {
        return this.post('/api/test-llm', config);
    }

    async saveSetup(config) {
        return this.post('/api/setup', config);
    }

    async startPipeline(videoPath = null) {
        return this.post('/api/start', { video_path: videoPath });
    }

    async getPipelineStatus(sessionId) {
        return this.get(`/api/status/${sessionId}`);
    }

    async cancelPipeline(sessionId) {
        return this.post(`/api/cancel/${sessionId}`);
    }

    async listOutputs() {
        return this.get('/output/list');
    }
}

// ============================================================================
// UI HELPERS
// ============================================================================

const UI = {
    showNotification(message, type = 'info') {
        const colors = {
            info: '#00d4aa',
            success: '#00ff88',
            error: '#ff4444',
            warning: '#ffaa00'
        };

        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${colors[type]};
            color: #000;
            border-radius: 8px;
            font-weight: 600;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto-remover después de 5 segundos
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    },

    formatDate(timestamp) {
        return new Date(timestamp * 1000).toLocaleString();
    },

    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    formatFileSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }
        return `${bytes.toFixed(2)} ${units[i]}`;
    }
};

// ============================================================================
// EXPORT GLOBAL INSTANCES
// ============================================================================

window.VIDEOAI = {
    WebSocketManager,
    APIClient,
    UI,
    
    // Instancias globales por defecto
    ws: null,
    api: new APIClient()
};

// Añadir estilos de animación para notificaciones
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

console.log('🎬 VIDEOAI JavaScript cargado');
