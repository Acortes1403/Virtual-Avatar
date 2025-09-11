// src/lib/expressionRules.js

// Helper: toma array de categorías => objeto {Name: score}
export function toMap(blendshapes) {
  const out = {};
  if (!blendshapes || !blendshapes.categories) return out;
  for (const c of blendshapes.categories) out[c.categoryName] = c.score;
  return out;
}

// Normaliza a [0,1]
const clamp01 = (x) => Math.max(0, Math.min(1, x || 0));

// Reglas heurísticas simples para FACE7
export function blendshapesToEmotion(blend) {
  const b = toMap(blend);

  // rasgos (si no existe, 0)
  const smile = (b.MouthSmileLeft + b.MouthSmileRight) / 2 || 0;
  const frown = (b.MouthFrownLeft + b.MouthFrownRight) / 2 || 0;
  const jawOpen = b.JawOpen || 0;
  const eyeWide = (b.EyeWideLeft + b.EyeWideRight) / 2 || 0;
  const browDown = (b.BrowDownLeft + b.BrowDownRight) / 2 || 0;
  const browUp = b.BrowInnerUp || 0;
  const noseSneer = (b.NoseSneerLeft + b.NoseSneerRight) / 2 || 0;
  const upperLipRaise = (b.UpperLipRaiseLeft + b.UpperLipRaiseRight) / 2 || 0;
  const mouthPress = (b.MouthPressLeft + b.MouthPressRight) / 2 || 0;
  const mouthStretch = (b.MouthStretchLeft + b.MouthStretchRight) / 2 || 0;

  // puntuaciones (0-1). Ajusta pesos/umbrales a gusto.
  const scores = {
    happy:
      clamp01(0.8 * smile - 0.2 * frown + 0.1 * browUp),
    sad:
      clamp01(0.7 * frown + 0.2 * mouthStretch - 0.1 * smile),
    surprised:
      clamp01(0.6 * jawOpen + 0.5 * eyeWide + 0.1 * browUp),
    angry:
      clamp01(0.6 * browDown + 0.3 * mouthPress + 0.1 * noseSneer),
    fearful:
      clamp01(0.5 * eyeWide + 0.3 * browUp + 0.2 * mouthStretch),
    disgusted:
      clamp01(0.6 * noseSneer + 0.3 * upperLipRaise + 0.1 * mouthPress),
    neutral: 0, // la calculamos al final como “lo que sobra”
  };

  // si todo es muy bajo, cae en neutral
  const maxNonNeutral = Math.max(
    scores.happy, scores.sad, scores.surprised,
    scores.angry, scores.fearful, scores.disgusted
  );
  scores.neutral = clamp01(1 - maxNonNeutral);

  // ganador
  let label = "neutral";
  let best = -1;
  for (const [k, v] of Object.entries(scores)) {
    if (v > best) { best = v; label = k; }
  }

  return { label, scores };
}
