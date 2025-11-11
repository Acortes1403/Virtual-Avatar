// src/hooks/useEmotionFusion.jsx
import { useState, useEffect, useCallback, useRef } from 'react';
import { isPepperAvailable } from '../lib/pepperState';

/**
 * Hook para gestionar la fusión de emociones (Face + Audio)
 *
 * Llama al endpoint /fusion/auto-fuse del backend para obtener
 * la emoción fusionada usando el sistema de votación 2oo2
 *
 * Respeta el estado de Pepper (proce): solo fusiona cuando Pepper está disponible
 *
 * @param {Object} options - Opciones de configuración
 * @param {string} options.room - ID de la room
 * @param {number} options.intervalMs - Intervalo entre fusiones (ms)
 * @param {boolean} options.enabled - Si el hook está habilitado
 * @param {Function} options.onUpdate - Callback cuando hay nueva fusión
 */
export default function useEmotionFusion({ room, intervalMs = 1000, enabled = true, onUpdate }) {
  const [fusedEmotion, setFusedEmotion] = useState(null);
  const [error, setError] = useState(null);

  const lastFusionRef = useRef({ label: null, ts: 0 });
  const intervalRef = useRef(null);
  const isProcessingRef = useRef(false); // Use ref instead of state to avoid re-renders
  const onUpdateRef = useRef(onUpdate); // Store callback in ref to avoid dependency issues

  // OPTIMIZACIÓN: Tracking de última detección por modalidad para debounce inteligente
  const lastDetectionTimeRef = useRef({ face: 0, audio: 0, lastCheck: 0 });

  const FUSION_API_URL = import.meta.env.VITE_FACE_API || 'http://localhost:8000';

  // Keep onUpdate ref updated
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  const performFusion = useCallback(async () => {
    if (!room || !enabled) {
      return;
    }

    if (isProcessingRef.current) {
      return; // Ya hay una fusión en proceso
    }

    try {
      isProcessingRef.current = true;

      // PASO 0: Verificar si Pepper está disponible (proce=1)
      try {
        const pepperIsAvailable = await isPepperAvailable(room);
        if (!pepperIsAvailable) {
          isProcessingRef.current = false;
          return;
        }
      } catch (error) {
        // Si falla el check, continuar con fusión de todas formas
      }

      // PASO 1: DEBOUNCE INTELIGENTE - Verificar si vale la pena hacer check
      // Solo verificar buffer-stats cada 2 segundos como mínimo
      const now = Date.now();
      const timeSinceLastCheck = now - lastDetectionTimeRef.current.lastCheck;

      if (timeSinceLastCheck < 2000) {
        // Muy pronto desde último check, skip para ahorrar requests
        // console.log(`[FUSION] ⏭️ Debounce skip: ${timeSinceLastCheck}ms < 2000ms`);
        isProcessingRef.current = false;
        return;
      }

      // PASO 2: Verificar si hay datos disponibles en el buffer
      const statsResponse = await fetch(`${FUSION_API_URL}/fusion/buffer-stats?room=${room}`);

      if (statsResponse.ok) {
        const stats = await statsResponse.json();

        // Actualizar timestamps de última detección
        lastDetectionTimeRef.current.lastCheck = now;
        if (stats.face_count > 0) {
          lastDetectionTimeRef.current.face = now;
        }
        if (stats.audio_count > 0) {
          lastDetectionTimeRef.current.audio = now;
        }

        // Solo intentar fusión si hay datos de AMBAS modalidades
        if (!stats.has_both) {
          isProcessingRef.current = false;
          return;
        }

        // OPTIMIZACIÓN ADICIONAL: Verificar que los datos sean frescos (< 10 segundos)
        const faceAge = stats.face_latest_age_ms || Infinity;
        const audioAge = stats.audio_latest_age_ms || Infinity;

        if (faceAge > 10000 || audioAge > 10000) {
          // Datos muy viejos, no fusionar
          isProcessingRef.current = false;
          return;
        }
      }

      // PASO 2: Intentar fusión
      const formData = new FormData();
      formData.append('room', room);

      const response = await fetch(`${FUSION_API_URL}/fusion/auto-fuse`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        // Si no hay detecciones disponibles, silencioso (no debería pasar después del check)
        if (response.status === 400) {
          return;
        }

        throw new Error(errorData?.detail || `HTTP error ${response.status}`);
      }

      const data = await response.json();

      // Verificar si la emoción ha cambiado
      const perfNow = performance.now();
      const isSameAsLast = lastFusionRef.current.label === data.emotion;
      const timeSinceLastFusion = perfNow - lastFusionRef.current.ts;

      if (!isSameAsLast || timeSinceLastFusion > 5000) {
        setFusedEmotion(data);
        lastFusionRef.current = { label: data.emotion, ts: perfNow };

        console.log(
          `[FUSION] ✨ New fusion: ${data.emotion} (${(data.confidence * 100).toFixed(1)}%) ` +
          `via ${data.strategy} | weights: face=${(data.weights.face * 100).toFixed(0)}% audio=${(data.weights.audio * 100).toFixed(0)}%`
        );

        // Use ref to avoid dependency on onUpdate
        if (onUpdateRef.current) {
          onUpdateRef.current(data);
        }
      }

      setError(null);
    } catch (err) {
      // Solo mostrar error si es algo crítico
      if (err.message && !err.message.includes('No hay detección')) {
        console.error('[FUSION] Error:', err);
        setError(err.message);
      }
    } finally {
      isProcessingRef.current = false;
    }
  }, [room, enabled, FUSION_API_URL]); // Removido onUpdate de dependencias

  useEffect(() => {
    if (!enabled || !room) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    console.log(`[FUSION] Starting fusion system for room: ${room}, interval: ${intervalMs}ms`);

    // Ejecutar inmediatamente
    performFusion();

    // Luego ejecutar periódicamente
    intervalRef.current = setInterval(performFusion, intervalMs);

    return () => {
      console.log(`[FUSION] Stopping fusion system for room: ${room}`);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, room, intervalMs]); // Removido performFusion de dependencias

  return {
    fusedEmotion,
    error,
    performFusion, // Exponer para llamadas manuales
  };
}
