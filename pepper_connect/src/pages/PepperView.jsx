// src/pages/PepperView.jsx
import React, { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";

export default function PepperView() {
  const videoRef = useRef(null);
  const pcRef = useRef(null);
  const socketRef = useRef(null);

  const [status, setStatus] = useState("Esperando conexión…");
  const [hasRemote, setHasRemote] = useState(false);
  const [needsTap, setNeedsTap] = useState(false);
  const [roomFull, setRoomFull] = useState(false);

  const room = useMemo(() => {
    const q = new URLSearchParams(window.location.search);
    return q.get("room") || "test";
  }, []);

  const SIGNALING_URL = useMemo(
    () => import.meta.env.VITE_SIGNALING_URL || `http://${window.location.hostname}:8080`,
    []
  );

  useEffect(() => {
    setStatus("Conectando señalización…");

    const socket = io(SIGNALING_URL, { transports: ["websocket", "polling"] });
    socketRef.current = socket;

    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun1.l.google.com:19302" },
      ],
    });
    pcRef.current = pc;

    pc.ontrack = (ev) => {
      const [stream] = ev.streams || [];
      if (videoRef.current && stream) {
        videoRef.current.srcObject = stream;
        setHasRemote(true);
        setStatus("Conectado ✅");
        videoRef.current.play().catch(() => setNeedsTap(true));
      }
    };

    pc.onicecandidate = (ev) => {
      if (ev.candidate) socket.emit("ice-candidate", { candidate: ev.candidate });
    };

    pc.onconnectionstatechange = () => {
      const st = pc.connectionState;
      if (st === "connected") setStatus("Conectado ✅");
      else if (st === "disconnected" || st === "failed")
        setStatus("Conexión perdida, esperando…");
    };

    socket.on("connect", () => {
      setStatus("Señalización conectada. Uniendo sala…");
      socket.emit("join", room);
    });

    socket.on("joined", ({ room: r }) => setStatus(`En sala: ${r}. Esperando offer…`));

    socket.on("room_full", ({ max }) => {
      setRoomFull(true);
      setStatus(`Sala llena (máx ${max}).`);
    });

    socket.on("offer", async ({ sdp }) => {
      try {
        setStatus("Recibí offer. Creando answer…");
        await pc.setRemoteDescription({ type: "offer", sdp });
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        socket.emit("answer", { sdp: answer.sdp });
        setStatus("Answer enviada. Esperando medios…");
      } catch (e) {
        console.error("Error procesando offer:", e);
        setStatus("Fallo procesando offer");
      }
    });

    socket.on("ice-candidate", async ({ candidate }) => {
      if (!candidate) return;
      try {
        await pc.addIceCandidate(candidate);
      } catch (e) {
        console.warn("addIceCandidate fallo:", e);
      }
    });

    socket.on("peer_left", () => {
      if (videoRef.current) videoRef.current.srcObject = null;
      setHasRemote(false);
      setStatus("El emisor salió. Esperando nuevo emisor…");
    });

    return () => {
      try {
        socket.emit("leave");
        socket.disconnect();
      } catch {}
      try {
        pc.getReceivers?.().forEach((r) => r.track?.stop?.());
        pc.getSenders?.().forEach((s) => s.track?.stop?.());
        pc.close();
      } catch {}
      socketRef.current = null;
      pcRef.current = null;
    };
  }, [SIGNALING_URL, room]);

  const handleTapToPlay = () => {
    const v = videoRef.current;
    if (!v) return;
    v.muted = false;
    v.play().then(() => setNeedsTap(false)).catch(() => {});
  };

  return (
    <div className="fixed inset-0 bg-black overflow-hidden">
      <video
        ref={videoRef}
        className="w-full h-full object-cover"
        autoPlay
        playsInline
        muted={needsTap}
      />

      {/* badge estado */}
      <div className="absolute top-3 left-3 bg-black/60 text-white text-sm px-3 py-1 rounded">
        {status}
      </div>

      {/* overlay si no hay remoto o sala llena */}
      {(!hasRemote || roomFull) && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="bg-black/60 text-white px-6 py-4 rounded-xl text-center max-w-[90%]">
            <div className="text-lg font-semibold">
              {roomFull ? "Sala llena" : "Esperando conexión…"}
            </div>
            <div className="text-sm opacity-80 mt-1">{status}</div>
          </div>
        </div>
      )}

      {/* botón para desbloquear audio en tablets */}
      {needsTap && hasRemote && !roomFull && (
        <button
          onClick={handleTapToPlay}
          className="absolute bottom-4 right-4 px-4 py-3 rounded-lg bg-white text-black shadow-lg hover:bg-gray-100 active:scale-95 transition"
          title="Reproducir audio"
        >
          🔊 Tocar para reproducir audio
        </button>
      )}
    </div>
  );
}
