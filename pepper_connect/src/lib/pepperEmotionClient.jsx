// src/lib/pepperEmotionClient.jsx

// ===== Config =====
const PEPPER_PROXY =
  import.meta.env?.VITE_PEPPER_PROXY_URL || "http://localhost:7070";

// Mapa archivo <-> emoción (incluye sinónimos)
const FILE_BY_EMOTION = {
  neutral: "neutral.txt",
  anger: "anger.txt",
  angry: "anger.txt",
  sad: "sad.txt",
  sadness: "sad.txt",
  surprise: "surprise.txt",
  surprised: "surprise.txt",
  disgust: "disgust.txt",
  disgusted: "disgust.txt",
  fear: "fear.txt",
  afraid: "fear.txt",
  scared: "fear.txt",
  happy: "happy.txt",
  joy: "happy.txt",
};

// ===== Normalización =====
export function normalizeEmotion(label) {
  if (!label) return "neutral";
  const s = String(label).toLowerCase().trim();
  if (["joy", "happy"].includes(s)) return "happy";
  if (["anger", "angry"].includes(s)) return "anger";
  if (["sad", "sadness"].includes(s)) return "sad";
  if (["surprise", "surprised"].includes(s)) return "surprise";
  if (["disgust", "disgusted"].includes(s)) return "disgust";
  if (["fear", "scared", "afraid"].includes(s)) return "fear";
  if (["neutral", "none", "..."].includes(s)) return "neutral";
  return "neutral";
}

// ===== Carga y caché de scripts =====
const SCRIPT_CACHE = new Map();

async function loadEmotionScript(assetsBase, emotion) {
  const base = (assetsBase || "").replace(/\/+$/, "");
  const fname = FILE_BY_EMOTION[emotion] || "neutral.txt";
  const key = `${base}/emotions/${fname}`;
  if (SCRIPT_CACHE.has(key)) return SCRIPT_CACHE.get(key);

  const res = await fetch(`${key}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`No se pudo leer ${fname} desde ${key}`);
  const text = await res.text();
  SCRIPT_CACHE.set(key, text);
  return text;
}

// ===== Cliente Pepper =====

// Deduplicación / Throttle (máx 2 req/s)
const lastSent = { label: null, ts: 0 };
const MIN_GAP_MS = 700;

/**
 * Ejecuta código Python directamente en Pepper (vía proxy 7070 por defecto).
 * @param {string} code - Código Python como string
 * @param {{signal?: AbortSignal, debug?: boolean}} [opts]
 * @returns {Promise<any>} JSON de respuesta (si lo hay)
 */
export async function runPepper(code, opts = {}) {
  const { signal, debug = false } = opts;
  const url = `${PEPPER_PROXY.replace(/\/+$/, "")}/pepper/execute_python`;

  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
    signal,
  });

  const ct = resp.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await resp.json() : await resp.text();

  if (debug) {
    // eslint-disable-next-line no-console
    console.debug("[PEPPER] status:", resp.status, "ct:", ct, "body:", body);
  }
  return body;
}

/**
 * Carga el script según la emoción y lo envía al intérprete de Pepper.
 * Respeta throttle/dedup para evitar spam.
 * @param {{
 *   emotionLabel: string,
 *   assetsBase?: string,     // normalmente import.meta.env.BASE_URL
 *   signal?: AbortSignal,
 *   debug?: boolean
 * }} params
 */
export async function triggerPepperEmotion({
  emotionLabel,
  assetsBase = "",
  signal,
  debug = false,
}) {
  const emotion = normalizeEmotion(emotionLabel);
  const now = performance.now();

  // evita re-enviar la misma emoción muy seguido
  if (emotion === lastSent.label && now - lastSent.ts < MIN_GAP_MS) {
    if (debug) console.debug("[PEPPER] throttled:", emotion);
    return { status: "skipped", reason: "throttle" };
  }

  const code = await loadEmotionScript(assetsBase, emotion);
  if (debug) console.debug("[PEPPER] emotion:", emotion, "script bytes:", code.length);

  const result = await runPepper(code, { signal, debug }).catch((e) => {
    if (debug) console.error("[PEPPER] fetch error:", e);
    return { status: "error", message: String(e) };
  });

  lastSent.label = emotion;
  lastSent.ts = performance.now();
  return result;
}
