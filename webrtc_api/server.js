// server.js
require("dotenv").config();
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");

const PORT = process.env.PORT || 8080;

// Si quieres restringir orígenes, pon CORS_ORIGIN="http://localhost:5173,http://TU_IP:5173"
// Si no está definido, dejamos CORS abierto en dev.
const parsedOrigins = (process.env.CORS_ORIGIN || "")
  .split(",")
  .map(s => s.trim())
  .filter(Boolean);
const ALLOWED_ORIGINS = parsedOrigins.length ? parsedOrigins : true;

const app = express();
app.use(
  cors({
    origin: ALLOWED_ORIGINS,
    methods: ["GET", "POST"],
    allowedHeaders: ["Content-Type"],
    credentials: false,
  })
);

// endpoints simples de salud
app.get("/", (_req, res) => res.send("Signaling server OK"));
app.get("/health", (_req, res) => res.json({ ok: true }));

const server = http.createServer(app);

const io = new Server(server, {
  // Importante: permitir ambos transportes
  transports: ["websocket", "polling"],
  cors: {
    origin: ALLOWED_ORIGINS,
    methods: ["GET", "POST"],
    credentials: false,
  },
  // tolerante con clientes viejos si hiciera falta
  allowEIO3: true,
});

// --- LÓGICA DE SALAS (máx 2 peers) ---
const MAX_PEERS = 2;

io.on("connection", (socket) => {
  const ip = socket.handshake.address;
  const origin = socket.handshake.headers?.origin;
  console.log(`🧷 connected: ${socket.id} from ${ip} (origin: ${origin || "n/a"})`);

  socket.on("join", (room) => {
    const roomRef = io.sockets.adapter.rooms.get(room);
    const numPeers = roomRef ? roomRef.size : 0;

    console.log(`➡️  ${socket.id} requests join room "${room}" (peers=${numPeers})`);

    if (numPeers >= MAX_PEERS) {
      console.log(`⛔ room "${room}" full`);
      socket.emit("room_full", { room, max: MAX_PEERS });
      return;
    }

    socket.join(room);
    socket.emit("joined", { room, id: socket.id });
    socket.to(room).emit("peer_joined", { id: socket.id });
    console.log(`✅ ${socket.id} joined "${room}"`);

    // Enrutado de mensajes WebRTC
    socket.on("offer", (payload) => {
      socket.to(room).emit("offer", payload);
      console.log(`📤 offer from ${socket.id} -> room "${room}"`);
    });

    socket.on("answer", (payload) => {
      socket.to(room).emit("answer", payload);
      console.log(`📤 answer from ${socket.id} -> room "${room}"`);
    });

    socket.on("ice-candidate", (payload) => {
      socket.to(room).emit("ice-candidate", payload);
      // normalmente no spameamos logs de ICE
    });

    // Salir explícito
    socket.on("leave", () => {
      socket.leave(room);
      socket.to(room).emit("peer_left", { id: socket.id });
      console.log(`↩️  ${socket.id} left "${room}"`);
    });
  });

  socket.on("disconnect", (reason) => {
    console.log(`🔌 disconnected: ${socket.id} (${reason})`);
  });

  socket.on("error", (err) => {
    console.warn(`⚠️  socket error ${socket.id}:`, err?.message || err);
  });
});

server.listen(PORT, () => {
  console.log(`🔌 Signaling server on http://0.0.0.0:${PORT}`);
  if (ALLOWED_ORIGINS === true) {
    console.log("CORS allowed: * (dev)");
  } else {
    console.log("CORS allowed:", ALLOWED_ORIGINS);
  }
});
