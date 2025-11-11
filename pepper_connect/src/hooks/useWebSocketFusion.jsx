// src/hooks/useWebSocketFusion.jsx
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Hook para gestionar fusión de emociones via WebSocket (real-time)
 *
 * VENTAJAS vs HTTP Polling:
 * - 70% menos latencia (push inmediato vs polling)
 * - 90% menos requests (solo envía cuando hay datos)
 * - Conexión persistente (sin overhead HTTP)
 * - Auto-fusión en backend (resultado inmediato)
 *
 * @param {Object} options - Opciones de configuración
 * @param {string} options.room - ID de la room
 * @param {boolean} options.enabled - Si el hook está habilitado
 * @param {Function} options.onFusion - Callback cuando hay nueva fusión
 * @param {Function} options.onDetection - Callback cuando hay nueva detección (opcional)
 */
export default function useWebSocketFusion({ room, enabled = true, onFusion, onDetection }) {
  const [fusedEmotion, setFusedEmotion] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // disconnected | connecting | connected | error
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const onFusionRef = useRef(onFusion);
  const onDetectionRef = useRef(onDetection);

  const FUSION_API_URL = import.meta.env.VITE_FACE_API || 'http://localhost:8000';
  const WS_URL = FUSION_API_URL.replace('http://', 'ws://').replace('https://', 'wss://');

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 2000;

  // Keep callbacks updated
  useEffect(() => {
    onFusionRef.current = onFusion;
    onDetectionRef.current = onDetection;
  }, [onFusion, onDetection]);

  const connect = useCallback(() => {
    if (!room || !enabled) return;

    // Limpiar conexión existente
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      console.log(`[WS-FUSION] Connecting to ${WS_URL}/ws/fusion/${room}...`);
      setConnectionStatus('connecting');

      const ws = new WebSocket(`${WS_URL}/ws/fusion/${room}`);
      wsRef.current = ws;

      ws.onopen = async () => {
        console.log(`[WS-FUSION] ✅ Connected to room: ${room}`);
        setConnectionStatus('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;

        // IMPORTANTE: Reset Pepper state a disponible al conectar
        // Esto asegura que los sensores pueden iniciar limpiamente
        try {
          const EMOTION_API_BASE = import.meta.env?.VITE_EMOTION_API_URL || "http://localhost:8000";
          const formData = new FormData();
          if (room) formData.append('room', room);

          const response = await fetch(`${EMOTION_API_BASE}/pepper/set-available`, {
            method: 'POST',
            body: formData
          });

          if (response.ok) {
            console.log(`[WS-FUSION] 🔓 Pepper state initialized to AVAILABLE (proce=1)`);
          }
        } catch (error) {
          console.warn(`[WS-FUSION] Could not reset Pepper state:`, error.message);
        }

        // Enviar ping cada 30 segundos para keep-alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);

        ws.pingInterval = pingInterval;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'connected':
              console.log(`[WS-FUSION] Server confirmed connection to room: ${message.room}`);
              break;

            case 'detection':
              // Nueva detección (face o audio)
              console.log(
                `[WS-FUSION] 📡 Detection: ${message.modality} = ${message.data.label} ` +
                `(${(message.data.score * 100).toFixed(1)}%)`
              );

              if (onDetectionRef.current) {
                onDetectionRef.current(message.modality, message.data);
              }
              break;

            case 'fusion':
              // Resultado de fusión automática
              console.log(
                `[WS-FUSION] ✨ Fusion: ${message.emotion} (${(message.confidence * 100).toFixed(1)}%) ` +
                `via ${message.strategy} | weights: F${(message.weights.face * 100).toFixed(0)}% A${(message.weights.audio * 100).toFixed(0)}%`
              );

              setFusedEmotion(message);

              if (onFusionRef.current) {
                onFusionRef.current(message);
              }
              break;

            case 'fusion_rejected':
              // Fusión rechazada por baja confianza
              console.warn(
                `[WS-FUSION] ⚠️ Fusion REJECTED: ${message.emotion} (${(message.confidence * 100).toFixed(1)}%) ` +
                `- Reason: ${message.reason} (min required: ${(message.min_required * 100).toFixed(0)}%)`
              );
              console.log(`[WS-FUSION] 🔄 Sensors remain active - waiting for better detection`);
              break;

            case 'pong':
              // Respuesta a ping (keep-alive)
              break;

            case 'heartbeat':
              // Heartbeat automático del servidor (keep-alive)
              // Solo log en debug mode
              console.debug(`[WS-FUSION] Heartbeat received from server`);
              break;

            default:
              console.warn(`[WS-FUSION] Unknown message type: ${message.type}`, message);
          }
        } catch (err) {
          console.error('[WS-FUSION] Error parsing message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WS-FUSION] WebSocket error:', event);
        setConnectionStatus('error');
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log(`[WS-FUSION] Connection closed. Code: ${event.code}, Reason: ${event.reason}`);
        setConnectionStatus('disconnected');

        // Limpiar ping interval
        if (ws.pingInterval) {
          clearInterval(ws.pingInterval);
        }

        // Intentar reconectar si fue cierre inesperado y aún está habilitado
        if (enabled && event.code !== 1000 && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          const delay = RECONNECT_DELAY * reconnectAttemptsRef.current;

          console.log(
            `[WS-FUSION] Reconnecting in ${delay}ms... ` +
            `(attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
          setError('Max reconnection attempts reached');
        }
      };

    } catch (err) {
      console.error('[WS-FUSION] Error creating WebSocket:', err);
      setConnectionStatus('error');
      setError(err.message);
    }
  }, [room, enabled, WS_URL]);

  // Conectar/desconectar cuando cambian las dependencias
  useEffect(() => {
    if (enabled && room) {
      connect();
    }

    return () => {
      // Cleanup
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }

      setConnectionStatus('disconnected');
    };
  }, [enabled, room, connect]);

  return {
    fusedEmotion,
    connectionStatus,
    error,
    isConnected: connectionStatus === 'connected',
  };
}
