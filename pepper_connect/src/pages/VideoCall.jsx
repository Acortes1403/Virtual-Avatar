// src/pages/VideoCall.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { io } from "socket.io-client";
import useExpressionDetection from "../hooks/useExpressionDetection";
import useAudioEmotionRecorder from "../hooks/useAudioEmotionRecorder";
import { triggerPepperEmotion, normalizeEmotion } from "../lib/pepperEmotionClient";

export default function VideoCall() {
  const userCamRef = useRef(null);
  const [userStream, setUserStream] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isCamOn, setIsCamOn] = useState(true);
  const [status, setStatus] = useState("");
  const [audioEmotion, setAudioEmotion] = useState(null);

  const lastUiRef = useRef({ label: null, score: null, ts: 0 }); // histeresis UI
  const pcRef = useRef(null);
  const socketRef = useRef(null);

  const navigate = useNavigate();

  // Detección de expresiones (usa el video local)
  const face = useExpressionDetection(userCamRef); // {label, score}

  const room = useMemo(() => {
    const u = new URL(window.location.href);
    return u.searchParams.get("room") || "test";
  }, []);

  const SIGNALING_URL = useMemo(
    () => import.meta.env.VITE_SIGNALING_URL || `http://${window.location.hostname}:8080`,
    []
  );

  // 1) Arrancar cámara/mic con filtros de micro activados
  useEffect(() => {
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 360 },
            frameRate: { ideal: 15, max: 15 },
          },
          audio: {
            channelCount: 1,
            noiseSuppression: true,
            echoCancellation: true,
            autoGainControl: true,
            sampleRate: 16000,
            sampleSize: 16,
          },
        });
        if (userCamRef.current) userCamRef.current.srcObject = stream;
        setUserStream(stream);
      } catch (e) {
        console.error("getUserMedia error:", e);
        setStatus("No se pudo acceder a cámara/mic.");
      }
    })();
  }, []);

  // 2) Socket.IO + WebRTC (emitimos OFFER)
  useEffect(() => {
    if (!userStream) return;

    const socket = io(SIGNALING_URL, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    const pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });
    pcRef.current = pc;

    userStream.getTracks().forEach((t) => pc.addTrack(t, userStream));

    pc.onicecandidate = (e) => {
      if (e.candidate) socket.emit("ice-candidate", { candidate: e.candidate });
    };

    pc.onconnectionstatechange = () => {
      const st = pc.connectionState;
      if (st === "connected") setStatus("Conectado con Pepper ✅");
      else if (st === "disconnected" || st === "failed")
        setStatus("Conexión perdida, intentando…");
    };

    socket.on("connect", () => {
      setStatus("Señalización conectada. Uniendo sala…");
      socket.emit("join", room);
    });

    socket.on("joined", async () => {
      try {
        setStatus("Creando y enviando offer…");
        const offer = await pc.createOffer({
          offerToReceiveAudio: true,
          offerToReceiveVideo: true,
        });
        await pc.setLocalDescription(offer);
        socket.emit("offer", { sdp: offer.sdp });
        setStatus("Offer enviada. Esperando answer…");
      } catch (e) {
        console.error("createOffer error:", e);
        setStatus("Error creando/enviando la oferta.");
      }
    });

    socket.on("peer_joined", async () => {
      try {
        const offer = await pc.createOffer({
          offerToReceiveAudio: true,
          offerToReceiveVideo: true,
        });
        await pc.setLocalDescription(offer);
        socket.emit("offer", { sdp: offer.sdp });
        setStatus("Offer reenviada. Esperando answer…");
      } catch (e) {
        console.error("re-offer error:", e);
      }
    });

    socket.on("answer", async ({ sdp }) => {
      try {
        await pc.setRemoteDescription({ type: "answer", sdp });
        setStatus("Answer recibida ✅");
      } catch (e) {
        console.error("setRemoteDescription answer error:", e);
      }
    });

    socket.on("ice-candidate", async ({ candidate }) => {
      if (!candidate) return;
      try {
        await pc.addIceCandidate(candidate);
      } catch (e) {
        console.warn("addIceCandidate error:", e);
      }
    });

    socket.on("room_full", ({ max }) => setStatus(`Sala llena (máx ${max}).`));
    socket.on("peer_left", () => setStatus("Pepper salió. Esperando reconexión…"));

    return () => {
      try { socket.emit("leave"); socket.disconnect(); } catch {}
      try {
        pc.getSenders().forEach((s) => s.track?.stop?.());
        pc.close();
      } catch {}
      socketRef.current = null;
      pcRef.current = null;
    };
  }, [userStream, SIGNALING_URL, room]);

  // Controles UI
  const toggleMic = () => {
    if (!userStream) return;
    userStream.getAudioTracks().forEach((t) => (t.enabled = !t.enabled));
    setIsMicOn((p) => !p);
  };

  const toggleCam = () => {
    if (!userStream) return;
    userStream.getVideoTracks().forEach((t) => (t.enabled = !t.enabled));
    setIsCamOn((p) => !p);
  };

  const confirmEndCall = () => {
    try { socketRef.current?.emit("leave"); socketRef.current?.disconnect(); } catch {}
    try {
      pcRef.current?.getSenders().forEach((s) => s.track?.stop?.());
      pcRef.current?.close();
    } catch {}
    if (userStream) userStream.getTracks().forEach((t) => t.stop());
    navigate("/");
  };

  // 3) Audio-emotion: hook optimizado (ráfagas + duty-cycle + backoff)
  useAudioEmotionRecorder({
    stream: userStream,
    apiUrl: import.meta.env.VITE_EMOTION_API_URL,
    room,
    intervalMs: 15000,
    onUpdate: (json) => {
      // Fallback neutral directo
      if (json?.fallback) {
        const next = { label: "neutral", score: null };
        lastUiRef.current = { ...next, ts: performance.now() };
        setAudioEmotion(next);
        return;
      }

      // Histeresis: evita micro-variaciones
      const mapped = json?.result?.mapped_emotion;
      const fused  = json?.result?.fused;
      const next = {
        label: mapped || fused?.label || "neutral",
        score: fused?.score ?? null,
      };

      const now = performance.now();
      const last = lastUiRef.current;
      const deltaScore = Math.abs((next.score ?? 0) - (last.score ?? 0));

      if (last.label === next.label && deltaScore < 0.1 && (now - last.ts) < 10000) {
        return; // ignora cambios pequeños recientes
      }

      lastUiRef.current = { ...next, ts: now };
      setAudioEmotion(next);
    },
  });

  // Dispara script en Pepper cuando cambie la emoción de AUDIO
  useEffect(() => {
    const label = normalizeEmotion(audioEmotion?.label);
    if (!label) return;

    const ctrl = new AbortController();
    const t = setTimeout(() => {
      triggerPepperEmotion({
        emotionLabel: label,
        assetsBase: import.meta.env.BASE_URL || "",
        signal: ctrl.signal,
        // debug: true,
      }).catch(() => {});
    }, 250); // debounce corto

    return () => { ctrl.abort(); clearTimeout(t); };
  }, [audioEmotion?.label]);

  const safeAudio = audioEmotion ?? { label: null, score: null };

  return (
    <div className="fixed inset-0 bg-black overflow-hidden">
      <div className="w-full h-full relative z-0">
        {/* Video Pepper (fondo opcional) */}
        <img
          src="http://pepper.local:8070/video_feed"
          alt="Vista de Pepper"
          className="w-full h-full object-cover"
        />

        {/* Estado de señalización */}
        {status && (
          <div className="absolute top-3 left-3 bg-black/60 text-white text-sm px-3 py-1 rounded">
            {status}
          </div>
        )}

        {/* Badges (cara + audio) */}
        <div className="absolute top-3 right-3 space-y-2 z-10">
          <div className="bg-black/60 text-white text-sm px-3 py-1 rounded">
            Cara: <b>{face?.label ?? "…"}</b>
          </div>
          <div className="bg-black/60 text-white text-sm px-3 py-1 rounded">
            Audio: <b>{safeAudio.label ?? "…"}</b>
            {safeAudio.score != null ? ` (${Math.round(safeAudio.score * 100)}%)` : ""}
          </div>
        </div>
      </div>

      {/* Preview local */}
      <div className="absolute bottom-28 right-6 w-[220px] h-[150px] rounded-lg overflow-hidden shadow-lg border border-white z-50 bg-black/40">
        <video ref={userCamRef} autoPlay muted playsInline className="w-full h-full object-cover" />
      </div>

      {/* Controles */}
      <div className="absolute bottom-0 left-0 w-full bg-black/70 py-3 flex justify-center gap-4 z-40">
        <button
          onClick={toggleMic}
          className={`${isMicOn ? "bg-purple-600 hover:bg-purple-500" : "bg-gray-500"} text-white p-3 rounded-full shadow transition`}
          title="Mic"
        >
          {isMicOn ? "🎤" : "🔇"}
        </button>
        <button
          onClick={toggleCam}
          className={`${isCamOn ? "bg-purple-600 hover:bg-purple-500" : "bg-gray-500"} text-white p-3 rounded-full shadow transition`}
          title="Cam"
        >
          {isCamOn ? "📹" : "📷"}
        </button>
        <button
          onClick={() => setShowModal(true)}
          className="bg-red-600 hover:bg-red-500 text-white p-3 rounded-full shadow transition"
          title="End"
        >
          ❌
        </button>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg shadow-lg w-[300px] text-center">
            <h2 className="text-lg font-semibold mb-4">¿Finalizar videollamada?</h2>
            <div className="flex justify-center gap-4">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded bg-gray-300 hover:bg-gray-400 transition"
              >
                Cancelar
              </button>
              <button
                onClick={confirmEndCall}
                className="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-500 transition"
              >
                Finalizar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
