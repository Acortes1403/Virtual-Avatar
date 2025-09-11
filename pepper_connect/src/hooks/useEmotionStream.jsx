// src/hooks/useEmotionStream.js
import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Captura audio del micrófono y envía un chunk cada intervalMs a /emotion/from-audio.
 * - Puedes pasar un MediaStream existente (por ejemplo, el de tu VideoCall) para no pedir permisos 2 veces.
 * - Si no pasas stream, el hook pedirá el micrófono.
 */
export default function useEmotionStream({
  apiBase = import.meta.env.VITE_EMOTION_API_URL || "http://localhost:8000",
  intervalMs = 5000,
  stream: externalStream = null,
  autoStart = true,
  onUpdate = null, // callback(result) en cada respuesta
} = {}) {
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);

  const mediaStreamRef = useRef(null);
  const recorderRef = useRef(null);
  const queueRef = useRef([]);           // cola de blobs pendientes
  const sendingRef = useRef(false);      // evita solapados
  const stoppedRef = useRef(false);

  const flushQueue = useCallback(async () => {
    if (sendingRef.current) return;
    const blob = queueRef.current.shift();
    if (!blob) return;

    sendingRef.current = true;
    try {
      const fd = new FormData();
      // Usa un nombre de archivo para Content-Disposition (el backend no lo necesita “de verdad”)
      fd.append(
        "audio",
        new File([blob], `chunk-${Date.now()}.webm`, { type: blob.type || "audio/webm" })
      );

      const resp = await fetch(`${apiBase}/emotion/from-audio`, {
        method: "POST",
        body: fd,
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();

      setLastResult(json);
      onUpdate && onUpdate(json);
    } catch (e) {
      setError(e);
      console.error("emotion_api error:", e);
    } finally {
      sendingRef.current = false;
      // si hay más blobs en cola, sigue
      if (queueRef.current.length) flushQueue();
    }
  }, [apiBase, onUpdate]);

  const start = useCallback(async () => {
    setError(null);
    stoppedRef.current = false;

    try {
      let stream = externalStream;
      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
      } else {
        mediaStreamRef.current = stream;
      }

      // Elegimos mimeType compatible (Chrome/Android → webm/opus)
      const preferred = "audio/webm;codecs=opus";
      const mimeType = MediaRecorder.isTypeSupported(preferred)
        ? preferred
        : (MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "");

      const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = rec;

      rec.ondataavailable = (ev) => {
        if (stoppedRef.current) return;
        if (ev.data && ev.data.size > 0) {
          queueRef.current.push(ev.data);
          flushQueue();
        }
      };
      rec.onerror = (e) => setError(e.error || e.name || e);

      // timeslice dispara ondataavailable cada intervalMs
      rec.start(intervalMs);
      setRunning(true);
    } catch (e) {
      setError(e);
      console.error("No se pudo iniciar el stream de audio:", e);
      setRunning(false);
    }
  }, [externalStream, intervalMs, flushQueue]);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    try {
      recorderRef.current?.stop();
    } catch {}
    recorderRef.current = null;

    // Si el stream lo creó el hook, lo detenemos
    if (!externalStream) {
      try {
        mediaStreamRef.current?.getTracks()?.forEach((t) => t.stop());
      } catch {}
    }
    mediaStreamRef.current = null;

    setRunning(false);
  }, [externalStream]);

  useEffect(() => {
    if (autoStart) start();
    return () => stop();
  }, [autoStart, start, stop]);

  return { running, lastResult, error, start, stop };
}
