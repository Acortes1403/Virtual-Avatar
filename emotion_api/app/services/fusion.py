# app/services/fusion.py
from typing import List, Dict
from ..config import settings
from .mapping import map_to_face7, FACE7

# FACE7 es un set; creamos lista de no-neutrales para iteraciones ordenadas si quieres
NON_NEUTRALS = [e for e in FACE7 if e != "neutral"]

def _to_face7(scores: List[Dict]) -> Dict[str, float]:
    d: Dict[str, float] = {}
    for r in scores:
        lab = map_to_face7(r["label"])
        d[lab] = d.get(lab, 0.0) + float(r["score"])
    for k in FACE7:
        d.setdefault(k, 0.0)
    return d

def _confidence(vec: Dict[str, float]) -> float:
    vals = sorted(vec.values(), reverse=True)
    return max(0.0, (vals[0] - vals[1])) if len(vals) >= 2 else 0.0

def _redistribute_neutral(f: Dict[str, float]) -> Dict[str, float]:
    """Mueve la masa de 'neutral' a las emociones no-neutrales en proporción a sus puntajes."""
    z = f.get("neutral", 0.0)
    if z <= 0:
        # no hay nada que redistribuir
        f["neutral"] = 0.0
        return f
    s = sum(f[k] for k in NON_NEUTRALS)
    if s > 0:
        for k in NON_NEUTRALS:
            f[k] += z * (f[k] / s)
    # neutral queda en cero
    f["neutral"] = 0.0
    return f

def fuse(text_scores: List[Dict], audio_scores: List[Dict]) -> Dict[str, float]:
    t = _to_face7(text_scores)
    a = _to_face7(audio_scores)

    # pesos base
    wt, wa = settings.weight_text, settings.weight_audio

    # pesos dinámicos según “confianza” (margen top1-top2)
    if settings.dynamic_weighting:
        ct, ca = _confidence(t), _confidence(a)
        wt *= (ct + 1e-6); wa *= (ca + 1e-6)
        s = wt + wa
        wt, wa = (wt/s, wa/s) if s > 0 else (0.5, 0.5)

    # fusión lineal
    fused = {k: wt * t[k] + wa * a[k] for k in FACE7}

    # === estrategia de neutral ===
    strat = (settings.neutral_strategy or "penalize").lower()
    if strat == "penalize":
        fused["neutral"] *= settings.neutral_penalty
    elif strat == "ban_redistribute":
        fused = _redistribute_neutral(fused)
    elif strat == "ban_pick":
        # no tocamos el vector, se ignora neutral en pick_label()
        pass
    else:
        # fallback seguro: penalize
        fused["neutral"] *= settings.neutral_penalty

    return fused

def pick_label(fused: Dict[str, float]) -> str:
    strat = (settings.neutral_strategy or "penalize").lower()

    # Si se decide “ban_pick”, ignoramos neutral al elegir
    if strat == "ban_pick":
        candidates = [(k, v) for k, v in fused.items() if k != "neutral"]
        if not candidates:
            return "happy"
        return max(candidates, key=lambda kv: kv[1])[0]

    # Comportamiento normal + preferencia por no-neutral si está “cerca”
    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    top_label, top_score = ordered[0]

    if settings.prefer_non_neutral and top_label == "neutral":
        for lab, sc in ordered[1:]:
            if lab != "neutral" and sc >= settings.non_neutral_min and (top_score - sc) <= settings.neutral_margin:
                return lab

    return top_label
