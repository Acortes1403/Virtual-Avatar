// proxy-pepper.cjs
const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');

const TARGET = process.env.PEPPER_TARGET || 'http://pepper.local:8070';
const PORT = process.env.PORT || 7070;

const app = express();

// CORS para tu front en Vite
app.use(cors({
  origin: ['http://localhost:5173', 'http://127.0.0.1:5173'],
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Log básico
app.use((req, _res, next) => {
  console.log(`[proxy] ${req.method} ${req.url}`);
  next();
});

// Proxy: /pepper/* -> TARGET/*
app.use('/pepper', createProxyMiddleware({
  target: TARGET,
  changeOrigin: true,
  secure: false,
  pathRewrite: { '^/pepper': '' },
}));

// Manejo de errores para que no salga silencioso
app.use((err, _req, res, _next) => {
  console.error('Proxy error:', err);
  res.status(502).send(String(err));
});

app.listen(PORT, () => {
  console.log(`✅ Pepper proxy listening on http://localhost:${PORT}`);
  console.log(`   → forwarding /pepper/* to ${TARGET}`);
});
