// src/hooks/useFaceYolo.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import { detectExpressionFromFrame } from "../lib/faceApi";
import { isPepperAvailable } from "../lib/pepperState";

const API_BASE = import.meta.env.VITE_FACE_API || "http://localhost:8000";
const ROUTE = import.meta.env.VITE_FACE_ROUTE || "/emotion/from-frame";

// TEMPORAL WINDOW CONFIGURATION (4 seconds aligned with audio)
const WINDOW_DURATION_MS = 4000;   // 4 seconds total window
const FRAMES_PER_WINDOW = 60;      // 60 frames (15 frames per second) - Reducido para evitar frames "a medio hablar"
const FRAME_INTERVAL_MS = WINDOW_DURATION_MS / FRAMES_PER_WINDOW; // ~67ms between frames
const BATCH_SIZE = 10;             // Analizar 10 frames en paralelo (6 batches total)
const IMG_SIZE = Number(import.meta.env.VITE_FACE_IMG_SIZE || 640);

/**
 * Agrega múltiples frames usando voting + averaging
 *
 * @param {Array} frames - Array de detecciones: [{label, score, scores}, ...]
 * @returns {Object} - Resultado agregado {label, score, confidence, frameCount, details}
 */
function aggregateFrames(frames) {
  if (!frames || frames.length === 0) {
    return { label: "neutral", score: 0, confidence: 0, frameCount: 0 };
  }

  // Contar votos por emoción
  const votes = {};
  const scoresByEmotion = {};

  frames.forEach(frame => {
    const emotion = frame.label || "neutral";
    const score = frame.score || 0;

    votes[emotion] = (votes[emotion] || 0) + 1;

    if (!scoresByEmotion[emotion]) {
      scoresByEmotion[emotion] = [];
    }
    scoresByEmotion[emotion].push(score);
  });

  // Encontrar emoción ganadora (más votos)
  let winnerEmotion = "neutral";
  let maxVotes = 0;

  Object.entries(votes).forEach(([emotion, count]) => {
    if (count > maxVotes) {
      maxVotes = count;
      winnerEmotion = emotion;
    }
  });

  // Calcular confidence: promedio de scores de la emoción ganadora
  const winnerScores = scoresByEmotion[winnerEmotion] || [0];
  const avgScore = winnerScores.reduce((sum, s) => sum + s, 0) / winnerScores.length;

  // Boost confidence si hay consenso fuerte (ej. 4/4 frames = misma emoción)
  const consensusRatio = maxVotes / frames.length;
  const confidence = avgScore * (0.7 + 0.3 * consensusRatio); // Boost hasta 30% por consenso

  return {
    label: winnerEmotion,
    score: confidence,
    confidence: confidence,
    frameCount: frames.length,
    votes: maxVotes,
    consensusRatio: consensusRatio,
    details: votes // Para debugging
  };
}

export default function useFaceYolo(videoRef, { room = "test" } = {}) {
  const [state, setState] = useState({
    label: "neutral",
    score: 0,
    ready: false,
    error: null,
    last: null,
    // Nuevo: información de agregación
    frameCount: 0,
    consensusRatio: 0,
    details: {}
  });

  // Temporal window state
  const frameBuffer = useRef([]); // Buffer de frames capturados en ventana actual
  const windowStartTime = useRef(0);
  const isCapturingWindow = useRef(false);

  const abortRef = useRef(null);
  const pendingRequest = useRef(false);
  const errorCount = useRef(0);
  const canvasRef = useRef(null);

  const getCanvas = () => {
    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
    }
    return canvasRef.current;
  };

  useEffect(() => {
    let cancelled = false;
    let timeoutId = null;
    let windowCount = 0;

    /**
     * Captura un frame localmente (solo canvas → blob, SIN análisis API)
     * RÁPIDO: ~10ms por frame
     */
    function captureFrameLocally() {
      const vid = videoRef.current;
      if (!vid || vid.readyState < 2) return null;

      try {
        const w = vid.videoWidth;
        const h = vid.videoHeight;
        if (!w || !h) return null;

        const canvas = getCanvas();
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(vid, 0, 0, w, h);

        // Retornar blob promise (no await aquí para velocidad)
        return new Promise((resolve) => {
          canvas.toBlob((blob) => {
            resolve(blob ? { blob, timestamp: Date.now() } : null);
          }, "image/jpeg", 0.85);
        });
      } catch (e) {
        console.warn(`⚠️ [FACE] Frame capture failed:`, e.message);
        return null;
      }
    }

    /**
     * Analiza un frame con la API de YOLOv8
     * LENTO: ~200-500ms por frame (por eso lo hacemos en batches)
     */
    async function analyzeFrame(frameData) {
      if (!frameData || !frameData.blob) return null;

      try {
        const controller = new AbortController();
        const requestTimeout = setTimeout(() => controller.abort(), 5000);

        const data = await detectExpressionFromFrame({
          apiBase: API_BASE,
          route: ROUTE,
          blob: frameData.blob,
          room,
          size: IMG_SIZE,
          signal: controller.signal,
        });

        clearTimeout(requestTimeout);

        // Extraer emoción principal
        const top =
          Array.isArray(data?.scores) && data.scores.length
            ? data.scores.reduce((a, b) => (b.score > a.score ? b : a))
            : { label: data?.label ?? "neutral", score: 0 };

        // Emotion-specific confidence thresholds to reduce false positives
        const EMOTION_THRESHOLDS = {
          'surprise': 0.55,  // Surprise often false positive - require higher confidence
          'fear': 0.55,      // Fear also prone to false positives
          'disgust': 0.50,   // Disgust can be confused with other emotions
          'default': 0.45    // Match backend threshold (increased from 0.3)
        };

        const requiredThreshold = EMOTION_THRESHOLDS[top.label] || EMOTION_THRESHOLDS['default'];

        // Fallback to neutral if confidence below emotion-specific threshold
        if (top.score < requiredThreshold) {
          top.label = "neutral";
          top.score = 0.5;
        }

        errorCount.current = 0;
        return { label: top.label, score: top.score, timestamp: frameData.timestamp };

      } catch (e) {
        if (e.name !== 'AbortError') {
          errorCount.current++;
        }
        return null;
      }
    }

    /**
     * Analiza un batch de frames en paralelo
     */
    async function analyzeBatch(frameBatch) {
      const results = await Promise.all(
        frameBatch.map(frame => analyzeFrame(frame))
      );
      return results.filter(r => r !== null);
    }

    /**
     * Captura una ventana completa de 60 frames (15 frames/segundo durante 4 segundos)
     * NUEVA ESTRATEGIA: Captura local primero, análisis paralelo después
     */
    async function captureWindow() {
      if (cancelled) return;

      // Check if Pepper is available
      try {
        const pepperIsAvailable = await isPepperAvailable(room);
        if (!pepperIsAvailable) {
          console.log('⏸️ [FACE] 🔒 Detection PAUSED - Pepper is BUSY executing animation (proce=0)');
          console.log('⏸️ [FACE] Will retry in 2s...');
          timeoutId = setTimeout(captureWindow, 2000);
          return;
        }
      } catch (error) {
        console.warn("Failed to check Pepper status, continuing:", error.message);
      }

      windowCount++;
      const windowId = windowCount;

      console.log(`📸 [FACE-WINDOW] Starting window ${windowId} (${FRAMES_PER_WINDOW} frames @ 15 fps)...`);

      isCapturingWindow.current = true;
      windowStartTime.current = Date.now();

      // FASE 1: CAPTURA LOCAL RÁPIDA (4 segundos exactos)
      const capturedFrames = [];
      for (let i = 0; i < FRAMES_PER_WINDOW; i++) {
        if (cancelled) break;

        const framePromise = captureFrameLocally();
        if (framePromise) {
          capturedFrames.push(framePromise);
        }

        // Esperar antes del siguiente frame (excepto en el último)
        if (i < FRAMES_PER_WINDOW - 1 && !cancelled) {
          await new Promise(resolve => setTimeout(resolve, FRAME_INTERVAL_MS));
        }
      }

      if (cancelled) return;

      const captureTime = Date.now() - windowStartTime.current;
      console.log(`📦 [FACE-WINDOW] Captured ${capturedFrames.length} frames in ${(captureTime / 1000).toFixed(1)}s`);

      // FASE 2: RESOLVER TODOS LOS BLOBS EN PARALELO
      const analysisStartTime = Date.now();
      const resolvedFrames = await Promise.all(capturedFrames);
      const validFrames = resolvedFrames.filter(f => f !== null);

      console.log(`🔍 [FACE-WINDOW] Starting analysis of ${validFrames.length} frames in ${Math.ceil(validFrames.length / BATCH_SIZE)} batches...`);

      // FASE 3: ANÁLISIS EN BATCHES PARALELOS
      const allResults = [];
      for (let i = 0; i < validFrames.length; i += BATCH_SIZE) {
        if (cancelled) break;

        const batch = validFrames.slice(i, i + BATCH_SIZE);
        const batchResults = await analyzeBatch(batch);
        allResults.push(...batchResults);
      }

      if (cancelled) return;

      const analysisTime = Date.now() - analysisStartTime;
      const totalTime = Date.now() - windowStartTime.current;

      console.log(
        `⚡ [FACE-WINDOW] Analysis completed in ${(analysisTime / 1000).toFixed(1)}s | ` +
        `${allResults.length}/${validFrames.length} frames analyzed successfully`
      );

      // FASE 4: AGREGACIÓN
      const aggregated = aggregateFrames(allResults);

      console.log(
        `✅ [FACE-WINDOW] Window ${windowId} TOTAL: ${(totalTime / 1000).toFixed(1)}s | ` +
        `Result: ${aggregated.label} (${(aggregated.confidence * 100).toFixed(0)}%) | ` +
        `${aggregated.votes}/${aggregated.frameCount} frames | ` +
        `consensus: ${(aggregated.consensusRatio * 100).toFixed(0)}%`
      );

      // Actualizar estado
      setState((s) => ({
        ...s,
        ready: true,
        error: null,
        label: aggregated.label,
        score: aggregated.confidence,
        frameCount: aggregated.frameCount,
        consensusRatio: aggregated.consensusRatio,
        details: aggregated.details,
        last: aggregated
      }));

      isCapturingWindow.current = false;

      // Programar siguiente ventana
      if (!cancelled) {
        // Esperar 2s antes de la siguiente ventana
        // Esto da tiempo a:
        // 1. Audio termine su grabación (~1s restante)
        // 2. Backend ejecute fusión y setee proce=0 si necesario
        // 3. WebSocket envíe mensaje al frontend
        timeoutId = setTimeout(captureWindow, 2000);
      }
    }

    // Inicializar
    setState((s) => ({ ...s, ready: false, error: null }));

    // DELAY INICIAL: 5s para sincronización entre sensores
    const SYNC_DELAY = 5000;  // 5s de sincronización entre sensores

    console.log(
      `👤 [FACE-YOLO] Initializing face detection:\n` +
      `   • Waiting ${SYNC_DELAY/1000}s for sensor synchronization...\n` +
      `   • Configuration: ${FRAMES_PER_WINDOW} frames/4s @ 15fps with parallel analysis`
    );

    timeoutId = setTimeout(captureWindow, SYNC_DELAY);

    return () => {
      cancelled = true;
      abortRef.current?.abort();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [videoRef, room]);

  return state; // {label, score, ready, error, last}
}
