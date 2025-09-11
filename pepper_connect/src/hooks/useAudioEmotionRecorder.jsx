// src/hooks/useAudioEmotionRecorder.js
import { useEffect, useRef } from "react";

/**
 * OPTIMIZACIONES CLAVE
 * - PRECHECK_MS ↓ (400ms) para reaccionar más rápido a voz.
 * - recordSpeechBurst(): graba ráfagas de 2–5s y corta si hay 600ms de silencio.
 * - Duty-cycle: si hay varios silencios seguidos, duplica temporalmente el intervalo.
 * - Backoff exponencial en errores/recursos insuficientes (1s→…→20s) + fallback neutral.
 */

const INTERVAL_MS = 15000;        // intervalo base (normal)
const PRECHECK_MS = 400;          // prechequeo rápido (voz) antes de grabar
const SILENCE_RMS = 0.015;        // umbral de silencio (ajusta 0.01–0.02)

const BURST_MIN_MS = 2000;        // ráfaga mínima 2s
const BURST_MAX_MS = 5000;        // ráfaga máxima 5s
const SILENCE_TAIL_MS = 600;      // corta si acumulas 600ms de silencio

const BACKOFF_BASE = 1000;        // 1s
const BACKOFF_MAX  = 20000;       // 20s
const MAX_CONSEC_FAILS = 6;       // reinicio suave si fallas demasiadas veces

const QUIET_HITS_FOR_SLOW = 3;    // # de prechequeos silenciosos para “modo lento”

function pickBestMime() {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    ""
  ];
  for (const t of candidates) {
    if (!t) return "";
    try { if (MediaRecorder.isTypeSupported(t)) return t; } catch {}
  }
  return "";
}

async function precheckLoudness(stream, ms = PRECHECK_MS) {
  if (!stream) return 0;
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const src = audioCtx.createMediaStreamSource(stream);
  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;
  src.connect(analyser);

  const buf = new Uint8Array(analyser.frequencyBinCount);
  let sum = 0, n = 0;
  const t0 = performance.now();

  const rmsAvg = await new Promise((resolve) => {
    function tick() {
      analyser.getByteTimeDomainData(buf);
      let acc = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        acc += v * v;
      }
      const rms = Math.sqrt(acc / buf.length);
      sum += rms; n++;

      if (performance.now() - t0 >= ms) {
        try { src.disconnect(); analyser.disconnect(); audioCtx.close(); } catch {}
        resolve(n ? sum / n : 0);
      } else {
        requestAnimationFrame(tick);
      }
    }
    tick();
  });

  return rmsAvg;
}

async function recordSpeechBurst(stream) {
  return new Promise((resolve, reject) => {
    const track = stream?.getAudioTracks?.()[0];
    if (!track) return reject(new Error("No hay pista de audio"));

    const audioOnly = new MediaStream([track]);

    // Analizador para detectar silencio mientras grabas
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = audioCtx.createMediaStreamSource(audioOnly);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.frequencyBinCount);

    const mimeType = pickBestMime();
    // bitrate bajo → menos bytes a red y CPU
    const rec = new MediaRecorder(
      audioOnly,
      mimeType ? { mimeType, audioBitsPerSecond: 32000 } : { audioBitsPerSecond: 32000 }
    );

    const chunks = [];
    rec.ondataavailable = (e) => e.data && chunks.push(e.data);
    rec.onerror = (e) => reject(e.error || new Error("MediaRecorder error"));
    rec.onstop = () => {
      try { src.disconnect(); analyser.disconnect(); audioCtx.close(); } catch {}
      const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
      resolve(blob);
    };

    const t0 = performance.now();
    let lastNonSilent = t0;
    let stopped = false;

    function isSilentFrame() {
      analyser.getByteTimeDomainData(buf);
      let acc = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        acc += v * v;
      }
      const rms = Math.sqrt(acc / buf.length);
      return rms < SILENCE_RMS;
    }

    function tick() {
      if (stopped) return;
      const now = performance.now();

      // No cortar antes del mínimo
      if (now - t0 < BURST_MIN_MS) {
        if (!isSilentFrame()) lastNonSilent = now;
        requestAnimationFrame(tick);
        return;
      }

      // Corta si superas el máximo o si acumulaste silencio prolongado
      const tooLong = (now - t0) >= BURST_MAX_MS;
      const tailSilent = isSilentFrame() && (now - lastNonSilent) >= SILENCE_TAIL_MS;

      if (tooLong || tailSilent) {
        stopped = true;
        try { rec.stop(); } catch {}
        return;
      }

      // Actualiza último instante no silencioso
      if (!isSilentFrame()) lastNonSilent = now;
      requestAnimationFrame(tick);
    }

    rec.start();
    requestAnimationFrame(tick);
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
    if (error.name === "TypeError") return true; // fetch fallido → tratar como saturación temporal
  }
  return false;
}

/**
 * Envía ráfagas de audio (2–5s) cuando hay voz, salta silencios y aplica backoff.
 * En ausencia de datos/errores, dispara onUpdate({fallback:"neutral"}).
 */
export default function useAudioEmotionRecorder({
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

  useEffect(() => {
    if (!enabled || !apiUrl) return;

    const pushNeutral = (reason) => onUpdate?.({ fallback: true, label: "neutral", score: null, reason });

    const schedule = (ms) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(loop, ms);
    };

    const resetBackoff = () => { failsRef.current = 0; backoffRef.current = BACKOFF_BASE; };
    const bumpBackoff = () => {
      failsRef.current += 1;
      backoffRef.current = Math.min(BACKOFF_MAX, backoffRef.current * 2);
      return backoffRef.current;
    };

    const loop = async () => {
      if (runningRef.current) return;
      runningRef.current = true;

      try {
        const hasAudio =
          !!stream &&
          stream.getAudioTracks &&
          stream.getAudioTracks().some(t => t.readyState === "live" && t.enabled !== false);

        if (!hasAudio) {
          pushNeutral("no_audio_track");
          runningRef.current = false;
          resetBackoff();
          return schedule(intervalMs);
        }

        // Pre-VAD corto: si silencio → duty-cycle (duplica intervalo tras varios silencios)
        const rms = await precheckLoudness(stream, PRECHECK_MS);
        if (rms < SILENCE_RMS) {
          quietHitsRef.current += 1;
          pushNeutral("silence");
          runningRef.current = false;
          resetBackoff();
          const slow = quietHitsRef.current >= QUIET_HITS_FOR_SLOW;
          return schedule(slow ? intervalMs * 2 : intervalMs);
        }
        // Hay voz → reset silencio y grabamos ráfaga
        quietHitsRef.current = 0;

        const blob = await recordSpeechBurst(stream);

        // Subimos al API
        const form = new FormData();
        form.append("audio", new File([blob], `clip_${Date.now()}.webm`, { type: blob.type || "audio/webm" }));
        form.append("room", room);

        let resp, json = null, text = null;
        try {
          resp = await fetch(`${apiUrl.replace(/\/+$/, "")}/emotion/from-audio`, {
            method: "POST",
            body: form,
          });
        } catch (error) {
          const delay = bumpBackoff();
          pushNeutral("fetch_error");
          runningRef.current = false;
          return schedule(delay);
        }

        const ct = resp.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          try { json = await resp.json(); } catch {}
        } else {
          try { text = await resp.text(); } catch {}
        }

        if (responseOrErrorIsInsufficient({ status: resp.status, headers: resp.headers, bodyText: text, json })) {
          const delay = bumpBackoff();
          pushNeutral("insufficient_resources");
          runningRef.current = false;
          return schedule(delay);
        }

        // Éxito
        resetBackoff();
        if (resp.ok && json && onUpdate) onUpdate(json);

        runningRef.current = false;
        schedule(intervalMs);
      } catch {
        const delay = bumpBackoff();
        pushNeutral("unexpected_error");
        runningRef.current = false;
        schedule(delay);
      } finally {
        if (failsRef.current >= MAX_CONSEC_FAILS) {
          resetBackoff();
        }
      }
    };

    loop();
    return () => {
      runningRef.current = false;
      if (timerRef.current) { clearTimeout(timerRef.current); timerRef.current = null; }
      resetBackoff();
    };
  }, [enabled, apiUrl, room, stream, intervalMs, onUpdate]);
}
