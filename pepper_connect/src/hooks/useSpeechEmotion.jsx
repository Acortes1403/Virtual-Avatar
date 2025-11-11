// src/hooks/useSpeechEmotion.jsx
import { useEffect, useRef } from "react";
import { isPepperAvailableForAudio } from "../lib/pepperState";

/**
 * Hook optimizado para reconocimiento de emociones por voz usando LSTM TESS
 * Modelo personalizado entrenado en dataset TESS con 99% de precisión
 *
 * CARACTERÍSTICAS:
 * - Usa el endpoint /emotion/from-speech con modelo LSTM
 * - Grabación fija de 4 segundos para compatibilidad con el modelo
 * - Control automático de estado de Pepper
 * - Alta calidad de audio (48kHz bitrate)
 * - Procesamiento de MFCC features
 */

// SINCRONIZACIÓN CON FACE DETECTION
// Face: 4s captura + 3-5s análisis = ~7-9s total por ventana
// Audio debe alinearse para que llegue justo después de face
const INTERVAL_MS = 8000;         // 8s intervalo (sincronizado con face)
const PRECHECK_MS = 1000;         // 1s de pre-análisis (más robusto que 400ms)
const SILENCE_RMS_MIN = 0.002;    // Umbral mínimo (muy sensible)
const SILENCE_RMS_MAX = 0.015;    // Umbral máximo (solo voz alta)
let SILENCE_RMS_ADAPTIVE = 0.005; // Umbral adaptativo (se ajusta dinámicamente)

const BURST_DURATION_MS = 4000;   // Duración fija de 4s para modelo LSTM
const SILENCE_TAIL_MS = 800;      // Corta en silencio si es necesario

const BACKOFF_BASE = 2000;        // 2s de backoff inicial
const BACKOFF_MAX = 25000;        // 25s máximo
const MAX_CONSEC_FAILS = 3;       // Reinicio después de 3 fallos

const QUIET_HITS_FOR_SLOW = 3;    // Modo lento después de 3 silencios consecutivos
const QUIET_HITS_FOR_ADAPTIVE = 5; // Ajustar umbral después de 5 silencios

// Estado global para VAD adaptativo (compartido entre ciclos)
const vadState = {
  recentRMS: [],           // Últimas mediciones RMS
  consecutiveQuiet: 0,     // Silencios consecutivos
  consecutiveLoud: 0,      // Voz detectada consecutiva
  ambientNoiseLevel: 0.003 // Nivel de ruido ambiente estimado
};

function pickBestMime() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    ""
  ];
  for (const t of candidates) {
    if (!t) return "";
    try {
      if (MediaRecorder.isTypeSupported(t)) return t;
    } catch {}
  }
  return "";
}

/**
 * VAD ADAPTATIVO: Pre-análisis de volumen con ajuste dinámico de umbral
 *
 * MEJORAS:
 * - Análisis más largo (1s vs 400ms) para mayor precisión
 * - Calcula min/max/avg RMS para detectar patrones
 * - Ajusta umbral basado en historial de detecciones
 * - Estima nivel de ruido ambiente
 *
 * @returns {Object} { rmsAvg, rmsMax, hasVoice, confidence }
 */
async function precheckLoudness(stream, ms = PRECHECK_MS) {
  if (!stream) return { rmsAvg: 0, rmsMax: 0, hasVoice: false, confidence: 0 };

  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const src = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;
  src.connect(analyser);

  const buf = new Uint8Array(analyser.frequencyBinCount);
  let sum = 0, n = 0, maxRMS = 0, minRMS = 1;
  const t0 = performance.now();

  const result = await new Promise((resolve) => {
    function tick() {
      analyser.getByteTimeDomainData(buf);
      let acc = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        acc += v * v;
      }
      const rms = Math.sqrt(acc / buf.length);
      sum += rms;
      n++;
      maxRMS = Math.max(maxRMS, rms);
      minRMS = Math.min(minRMS, rms);

      if (performance.now() - t0 >= ms) {
        try {
          src.disconnect();
          analyser.disconnect();
          audioCtx.close();
        } catch {}

        const rmsAvg = n ? sum / n : 0;
        const rmsDynamic = maxRMS - minRMS; // Rango dinámico (indica variación)

        resolve({ rmsAvg, rmsMax: maxRMS, rmsMin: minRMS, rmsDynamic });
      } else {
        requestAnimationFrame(tick);
      }
    }
    tick();
  });

  // Actualizar historial de RMS para aprendizaje
  vadState.recentRMS.push(result.rmsAvg);
  if (vadState.recentRMS.length > 10) {
    vadState.recentRMS.shift(); // Mantener últimas 10 mediciones
  }

  // Estimar ruido ambiente (promedio de valores bajos)
  const sortedRMS = [...vadState.recentRMS].sort((a, b) => a - b);
  vadState.ambientNoiseLevel = sortedRMS.slice(0, 3).reduce((a, b) => a + b, 0) / 3;

  // DECISIÓN ADAPTATIVA: ¿hay voz?
  // Criterio 1: RMS promedio supera umbral adaptativo
  // Criterio 2: Hay variación dinámica (no es ruido constante)
  const threshold = Math.max(SILENCE_RMS_MIN, vadState.ambientNoiseLevel * 1.5);
  SILENCE_RMS_ADAPTIVE = Math.min(SILENCE_RMS_MAX, threshold);

  const hasVoice = result.rmsAvg >= SILENCE_RMS_ADAPTIVE && result.rmsDynamic > 0.002;

  // Confidence basado en qué tan por encima del umbral está
  const confidence = hasVoice ? Math.min(1.0, result.rmsAvg / SILENCE_RMS_ADAPTIVE) : 0;

  return {
    ...result,
    hasVoice,
    confidence,
    threshold: SILENCE_RMS_ADAPTIVE,
    ambientNoise: vadState.ambientNoiseLevel
  };
}

async function recordSpeechBurst(stream) {
  return new Promise((resolve, reject) => {
    const track = stream?.getAudioTracks?.()?.[0];
    if (!track) {
      console.error("❌ No audio track found");
      return reject(new Error("No hay pista de audio"));
    }

    console.log("🎙️ Audio track state:", {
      enabled: track.enabled,
      muted: track.muted,
      readyState: track.readyState,
      label: track.label
    });

    const audioOnly = new MediaStream([track]);

    const mimeType = pickBestMime();
    console.log("🎬 Recording with mimeType:", mimeType || "default");

    // Bitrate alto para LSTM (mejor calidad de MFCC features)
    const rec = new MediaRecorder(
      audioOnly,
      mimeType ? { mimeType, audioBitsPerSecond: 64000 } : { audioBitsPerSecond: 64000 }
    );

    const chunks = [];
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        console.log("📦 Audio chunk received:", e.data.size, "bytes");
        chunks.push(e.data);
      }
    };
    rec.onerror = (e) => {
      console.error("❌ MediaRecorder error:", e);
      reject(e.error || new Error("MediaRecorder error"));
    };
    rec.onstop = () => {
      console.log("⏹️ Recording stopped. Total chunks:", chunks.length);
      const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
      console.log("📁 Final blob size:", blob.size, "bytes");
      resolve(blob);
    };

    // Grabar exactamente 4 segundos (duración fija para modelo LSTM)
    // Usar timeslice de 1000ms para garantizar que se capturan datos
    console.log("▶️ Starting recording for", BURST_DURATION_MS, "ms");
    rec.start(1000); // Request data every 1 second
    setTimeout(() => {
      console.log("⏸️ Stopping recording...");
      try { rec.stop(); } catch (e) {
        console.error("Error stopping recorder:", e);
      }
    }, BURST_DURATION_MS);
  });
}

function responseOrErrorIsInsufficient({ status, headers, bodyText, json, error }) {
  const lc = (s) => (s || "").toLowerCase();
  if (status === 429 || status === 503) return true;

  if (lc(bodyText).includes("insufficient") || lc(bodyText).includes("out of memory")) return true;
  const j = json ? lc(JSON.stringify(json)) : "";
  if (j.includes("insufficient") || j.includes("out of memory")) return true;

  if (error) {
    const msg = lc(error.message);
    if (msg.includes("insufficient") || msg.includes("resources")) return true;
    if (error.name === "TypeError") return true;
  }
  return false;
}

/**
 * Hook para reconocimiento de emociones por voz usando LSTM TESS
 *
 * @param {Object} params
 * @param {MediaStream} params.stream - Stream de audio del micrófono
 * @param {string} params.apiUrl - URL base de la API de emociones
 * @param {string} params.room - Identificador de sala
 * @param {function} params.onUpdate - Callback cuando se detecta una emoción
 * @param {boolean} params.enabled - Si el hook está habilitado
 * @param {number} params.intervalMs - Intervalo entre detecciones
 */
export default function useSpeechEmotion({
  stream,
  apiUrl,
  room = "test",
  onUpdate = null,
  enabled = true,
  intervalMs = INTERVAL_MS,
}) {
  const runningRef = useRef(false);
  const timerRef = useRef(null);
  const failsRef = useRef(0);
  const backoffRef = useRef(BACKOFF_BASE);
  const quietHitsRef = useRef(0);
  const enabledRef = useRef(enabled);
  const cleanupRef = useRef(false);
  const streamRef = useRef(stream);
  const intervalMsRef = useRef(intervalMs);
  const onUpdateRef = useRef(onUpdate);

  useEffect(() => {
    if (!enabled || !apiUrl) return;

    const pushNeutral = (reason) => onUpdateRef.current?.({
      fallback: true,
      label: "neutral",
      score: 0.5,
      reason,
      model: "lstm-tess-custom"
    });

    const pushSilence = (reason) => {
      // IMPORTANTE: En silencio, enviar "neutral" en lugar de "silence"
      // Esto permite que la fusión funcione correctamente con face
      // Si enviamos "silence", el buffer no puede fusionar
      onUpdateRef.current?.({
        fallback: true,
        label: "neutral",  // Cambiar de "silence" a "neutral"
        score: 0.35,       // Baja confianza (antes 0.0)
        reason,
        model: "lstm-tess-custom-silence"
      });
    };

    const schedule = (ms) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(loop, ms);
    };

    const resetBackoff = () => {
      failsRef.current = 0;
      backoffRef.current = BACKOFF_BASE;
    };

    const bumpBackoff = () => {
      failsRef.current += 1;
      backoffRef.current = Math.min(BACKOFF_MAX, backoffRef.current * 2);
      return backoffRef.current;
    };

    const loop = async () => {
      // Verificar si el hook está deshabilitado o en cleanup
      if (!enabledRef.current || cleanupRef.current || runningRef.current) {
        return;
      }
      runningRef.current = true;

      console.log(`🔄 [SPEECH-V3] Audio detection loop starting`);

      try {
        const currentStream = streamRef.current;
        const hasAudio =
          !!currentStream &&
          currentStream.getAudioTracks &&
          currentStream.getAudioTracks().some(t => t.readyState === "live" && t.enabled !== false);

        if (!hasAudio) {
          pushNeutral("no_audio_track");
          runningRef.current = false;
          resetBackoff();
          // Solo reagendar si seguimos habilitados
          if (enabledRef.current && !cleanupRef.current) {
            return schedule(intervalMsRef.current);
          }
          return;
        }

        // Verificar estado de Pepper antes de procesar audio
        try {
          const pepperIsAvailable = await isPepperAvailableForAudio(room);
          if (!pepperIsAvailable) {
            console.log(`⏸️ [SPEECH] 🔒 Detection PAUSED - Pepper is BUSY executing animation (proce=0)`);
            console.log(`⏸️ [SPEECH] Will retry in ${(intervalMsRef.current * 1.5 / 1000).toFixed(1)}s...`);
            pushNeutral("pepper_busy");
            runningRef.current = false;
            resetBackoff();
            // Solo reagendar si seguimos habilitados
            if (enabledRef.current && !cleanupRef.current) {
              return schedule(intervalMsRef.current * 1.5);
            }
            return;
          }
        } catch (error) {
          console.warn("Failed to check Pepper status for speech audio, continuing:", error.message);
        }

        // VAD ADAPTATIVO: verificar si hay voz antes de grabar
        const vadResult = await precheckLoudness(currentStream, PRECHECK_MS);

        console.log(
          `🔊 [SPEECH-V3] VAD check: RMS=${vadResult.rmsAvg.toFixed(4)} (max=${vadResult.rmsMax.toFixed(4)}) | ` +
          `threshold=${vadResult.threshold.toFixed(4)} (adaptive) | ` +
          `ambient=${vadResult.ambientNoise.toFixed(4)} | ` +
          `detected=${vadResult.hasVoice ? 'VOICE ✓' : 'SILENCE ✗'} (${(vadResult.confidence * 100).toFixed(0)}%)`
        );

        if (!vadResult.hasVoice) {
          // SILENCIO DETECTADO
          vadState.consecutiveQuiet += 1;
          vadState.consecutiveLoud = 0;
          quietHitsRef.current += 1;

          // Log solo en primera detección o cada 5 veces
          if (quietHitsRef.current === 1 || quietHitsRef.current % 5 === 0) {
            console.log(
              `😴 [SPEECH-V3] Silence #${quietHitsRef.current} - ` +
              `RMS ${vadResult.rmsAvg.toFixed(4)} < threshold ${vadResult.threshold.toFixed(4)}`
            );
          }

          // Ajustar umbral si hay muchos silencios consecutivos (puede ser ruido ambiente alto)
          if (vadState.consecutiveQuiet >= QUIET_HITS_FOR_ADAPTIVE) {
            const oldThreshold = SILENCE_RMS_ADAPTIVE;
            SILENCE_RMS_ADAPTIVE = Math.min(SILENCE_RMS_MAX, SILENCE_RMS_ADAPTIVE * 1.1);
            console.log(
              `📊 [SPEECH-VAD] Adaptive threshold increased: ${oldThreshold.toFixed(4)} → ${SILENCE_RMS_ADAPTIVE.toFixed(4)} ` +
              `(${vadState.consecutiveQuiet} consecutive silences)`
            );
            vadState.consecutiveQuiet = 0;
          }

          pushSilence("silence");
          runningRef.current = false;
          resetBackoff();

          // Solo reagendar si seguimos habilitados
          if (enabledRef.current && !cleanupRef.current) {
            // Modo lento después de varios silencios
            const slow = quietHitsRef.current >= QUIET_HITS_FOR_SLOW;
            const nextInterval = slow ? intervalMsRef.current * 1.5 : intervalMsRef.current;
            return schedule(nextInterval);
          }
          return;
        }

        // VOZ DETECTADA → reset contador de silencio y grabar
        vadState.consecutiveLoud += 1;
        vadState.consecutiveQuiet = 0;
        quietHitsRef.current = 0;

        console.log(
          `🎤 [SPEECH-V3] Voice detected (confidence: ${(vadResult.confidence * 100).toFixed(0)}%), ` +
          `recording ${BURST_DURATION_MS}ms burst...`
        );

        const blob = await recordSpeechBurst(currentStream);

        // Crear FormData para el endpoint LSTM
        const form = new FormData();
        form.append("audio", new File([blob], `lstm_clip_${Date.now()}.webm`, {
          type: blob.type || "audio/webm"
        }));
        form.append("room", room);

        let resp, json = null, text = null;
        try {
          // Usar el endpoint /from-speech con modelo LSTM
          const audioApiUrl = apiUrl.replace(/\/+$/, "");
          resp = await fetch(`${audioApiUrl}/emotion/from-speech`, {
            method: "POST",
            body: form,
          });
        } catch (error) {
          const delay = bumpBackoff();
          console.error("❌ LSTM Speech API fetch error:", error);
          pushNeutral("fetch_error");
          runningRef.current = false;
          // Solo reagendar si seguimos habilitados
          if (enabledRef.current && !cleanupRef.current) {
            return schedule(delay);
          }
          return;
        }

        const ct = resp.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          try { json = await resp.json(); } catch {}
        } else {
          try { text = await resp.text(); } catch {}
        }

        if (responseOrErrorIsInsufficient({
          status: resp.status,
          headers: resp.headers,
          bodyText: text,
          json
        })) {
          const delay = bumpBackoff();
          console.warn("⚠️ Speech API insufficient resources, backing off...");
          pushNeutral("insufficient_resources");
          runningRef.current = false;
          // Solo reagendar si seguimos habilitados
          if (enabledRef.current && !cleanupRef.current) {
            return schedule(delay);
          }
          return;
        }

        // Éxito
        resetBackoff();
        if (resp.ok && json && onUpdateRef.current) {
          console.log("✅ Speech emotion detected:", json.label, `(${(json.score * 100).toFixed(1)}%)`);
          onUpdateRef.current(json);
        }

        runningRef.current = false;
        // Solo reagendar si seguimos habilitados
        if (enabledRef.current && !cleanupRef.current) {
          schedule(intervalMsRef.current);
        }

      } catch (error) {
        const delay = bumpBackoff();
        console.error("❌ Speech emotion detection error:", error);
        pushNeutral("unexpected_error");
        runningRef.current = false;
        // Solo reagendar si seguimos habilitados
        if (enabledRef.current && !cleanupRef.current) {
          schedule(delay);
        }
      } finally {
        if (failsRef.current >= MAX_CONSEC_FAILS) {
          console.warn("⚠️ Too many consecutive failures, resetting backoff");
          resetBackoff();
        }
      }
    };

    // Actualizar referencias de estado
    enabledRef.current = enabled;
    cleanupRef.current = false;
    streamRef.current = stream;
    intervalMsRef.current = intervalMs;
    onUpdateRef.current = onUpdate;

    // DELAY INICIAL: 5s para sincronización entre sensores
    const SYNC_DELAY = 5000;  // 5s de sincronización entre sensores

    console.log(
      `🚀 [SPEECH-V3] Initializing LSTM TESS emotion detection:\n` +
      `   • Interval: ${INTERVAL_MS}ms (synchronized with face: ~8s)\n` +
      `   • VAD: Adaptive threshold (${SILENCE_RMS_ADAPTIVE.toFixed(4)} initial)\n` +
      `   • Recording: ${BURST_DURATION_MS}ms fixed duration\n` +
      `   • Precheck: ${PRECHECK_MS}ms voice activity detection\n` +
      `   • Waiting ${SYNC_DELAY/1000}s for sensor synchronization...`
    );

    // Solo iniciar si está habilitado
    // IMPORTANTE: Delay de 5s para sincronización entre sensores
    // Face inicia su primera ventana después de 5s, audio debe empezar al mismo tiempo
    if (enabled) {
      timerRef.current = setTimeout(() => {
        console.log("✅ Audio detection synchronized - starting first capture");
        loop();
      }, SYNC_DELAY);
    }

    return () => {
      // Marcar como deshabilitado y en cleanup
      enabledRef.current = false;
      cleanupRef.current = true;
      runningRef.current = false;

      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      resetBackoff();
      console.log("🛑 Speech emotion detection stopped");
    };
  }, [enabled, apiUrl, room]); // Reducir dependencias para evitar reinicios innecesarios
}