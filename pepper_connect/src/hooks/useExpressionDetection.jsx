// src/hooks/useExpressionDetection.jsx

import { useEffect, useRef, useState } from "react";
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

const WASM_ROOT = import.meta.env.VITE_FACE_WASM_ROOT || "/mediapipe/vision";
const TASK_PATH = import.meta.env.VITE_FACE_TASK_PATH || "/mediapipe/face_landmarker.task";

// --------- Reglas simples a partir de blendshapes ---------
function pickExpression(blendshapes) {
  // blendshapes: [{categoryName, score}, ...]
  // Mapeo muy básico; ajusta a tu gusto:
  const get = (name) =>
    blendshapes.find((b) => b.categoryName === name)?.score ?? 0;

  // Indicadores rápidos
  const smileL = get("mouthSmileLeft");
  const smileR = get("mouthSmileRight");
  const frown   = get("mouthFrownLeft") + get("mouthFrownRight");
  const jawOpen = get("jawOpen");
  const browUp  = get("browInnerUp") + get("browOuterUpLeft") + get("browOuterUpRight");
  const mouthOpen = get("mouthOpen") || jawOpen;

  const joy = (smileL + smileR) / 2;
  const anger = frown * 0.6 + (get("browDownLeft") + get("browDownRight")) * 0.4;
  const surprise = Math.max(browUp, mouthOpen);
  const sadness = get("mouthStretchLeft") * 0.5 + get("mouthStretchRight") * 0.5 + get("mouthPucker") * 0.3;

  // Normalización muy ligera
  const scores = {
    Happy: joy,
    Angry: anger,
    Surprised: surprise,
    Sad: sadness,
    Neutral: 0.25, // base
  };

  // Penaliza Neutral si hay una emoción clara
  const maxEmotion = Object.entries(scores).reduce(
    (a, b) => (b[1] > a[1] ? b : a),
    ["Neutral", 0]
  );

  // Umbral para no “saltar” por ruido
  const TH = 0.35; // ajusta
  if (maxEmotion[0] !== "Neutral" && maxEmotion[1] >= TH) {
    return { label: maxEmotion[0], score: maxEmotion[1] };
  }
  return { label: "Neutral", score: 1 - Math.min(0.9, maxEmotion[1]) };
}

// Suavizado exponencial para evitar parpadeos
function smooth(prev, next, alpha = 0.5) {
  if (!prev) return next;
  if (prev.label !== next.label) return next; // cambio fuerte: saltar
  return {
    label: next.label,
    score: prev.score * (1 - alpha) + next.score * alpha,
  };
}

/**
 * Hook de detección de expresiones con MediaPipe Face Landmarker.
 * @param {React.RefObject<HTMLVideoElement>} videoRef - video local (getUserMedia)
 * @returns {{label: string, score: number, ready: boolean, error: string|null}}
 */
export default function useExpressionDetection(videoRef) {
  const [state, setState] = useState({
    label: "Neutral",
    score: 0,
    ready: false,
    error: null,
  });

  const lmRef = useRef(null);
  const rafRef = useRef(0);
  const lastTSRef = useRef(0);
  const smoothedRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        // Cargar runtime WASM desde /public/mediapipe/vision
        const vision = await FilesetResolver.forVisionTasks(WASM_ROOT);
        if (cancelled) return;

        // Cargar modelo .task desde /public/mediapipe/face_landmarker.task
        const faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: TASK_PATH },
          runningMode: "VIDEO",
          numFaces: 1,
          outputFaceBlendshapes: true,
        });
        if (cancelled) {
          faceLandmarker.close();
          return;
        }
        lmRef.current = faceLandmarker;
        setState((s) => ({ ...s, ready: true, error: null }));

        // Esperar a que el <video> esté listo
        const vid = videoRef.current;
        if (!vid) return;

        if (vid.readyState < 2) {
          await new Promise((res) => {
            const onLoaded = () => {
              vid.removeEventListener("loadeddata", onLoaded);
              res();
            };
            vid.addEventListener("loadeddata", onLoaded);
          });
        }

        // Bucle ~10 FPS
        const targetIntervalMs = 100; // 10 fps
        const loop = () => {
          if (cancelled || !lmRef.current || !videoRef.current) return;
          const now = performance.now();
          if (now - lastTSRef.current >= targetIntervalMs) {
            lastTSRef.current = now;
            try {
              const res = lmRef.current.detectForVideo(videoRef.current, now);
              const bs = res?.faceBlendshapes?.[0]?.categories || [];
              if (bs.length > 0) {
                const picked = pickExpression(bs);
                smoothedRef.current = smooth(smoothedRef.current, picked, 0.4);
                setState((s) => ({
                  ...s,
                  label: smoothedRef.current.label,
                  score: smoothedRef.current.score,
                }));
              }
            } catch (e) {
              // Si falla una iteración, no tumbar el bucle
              // console.debug("detect error:", e);
            }
          }
          rafRef.current = requestAnimationFrame(loop);
        };
        rafRef.current = requestAnimationFrame(loop);
      } catch (err) {
        console.error("FaceLandmarker init error:", err);
        setState((s) => ({
          ...s,
          error:
            err?.message ||
            "Fallo iniciando FaceLandmarker. Verifica rutas de WASM/MODEL.",
          ready: false,
        }));
      }
    }

    init();

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
      try {
        lmRef.current?.close();
      } catch {}
      lmRef.current = null;
    };
  }, [videoRef]);

  return state; // {label, score, ready, error}
}
