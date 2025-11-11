# app/routers/services/fusion.py
from typing import List, Dict
from app.config import settings
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

def _emotion_diversity(vec: Dict[str, float]) -> float:
    """Measure how diverse the emotion distribution is (higher = more diverse)."""
    vals = [v for v in vec.values() if v > 0]
    if len(vals) <= 1:
        return 0.0

    # Calculate entropy-like measure
    total = sum(vals)
    if total == 0:
        return 0.0

    entropy = 0.0
    for v in vals:
        if v > 0:
            p = v / total
            entropy += p * (-1) * (p ** 0.5)  # Modified entropy

    return entropy

def _detect_emotional_intensity(text_scores: List[Dict], audio_scores: List[Dict]) -> float:
    """Detect overall emotional intensity from both sources."""

    # Check for pattern-detected emotions in text (these suggest high intensity)
    text_pattern_emotions = [e for e in text_scores if e["label"] != "neutral" and e["score"] > 0.5]

    # Check for high-energy emotions in audio
    audio_high_emotions = [e for e in audio_scores if e["label"] in ["fear", "anger", "surprise"] and e["score"] > 0.3]

    intensity = 0.0

    # Text patterns suggest urgency
    if text_pattern_emotions:
        intensity += 0.4

    # Audio energy suggests emotion
    if audio_high_emotions:
        intensity += 0.3

    # Multiple emotion sources suggest high intensity
    total_emotions = len([e for e in text_scores + audio_scores if e["label"] != "neutral" and e["score"] > 0.2])
    if total_emotions > 2:
        intensity += 0.3

    return min(1.0, intensity)

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
            if k in f:
                f[k] += z * (f[k] / s)
    else:
        # If no non-neutral emotions, distribute equally among fear, surprise, anger
        default_emotions = ["fear", "surprise", "anger"]
        for k in default_emotions:
            f[k] = f.get(k, 0.0) + z / len(default_emotions)

    # neutral queda en cero
    f["neutral"] = 0.0
    return f

def fuse(text_scores: List[Dict], audio_scores: List[Dict]) -> Dict[str, float]:
    t = _to_face7(text_scores)
    a = _to_face7(audio_scores)

    # Enhanced dynamic weighting
    intensity = _detect_emotional_intensity(text_scores, audio_scores)

    # Base weights
    wt, wa = settings.weight_text, settings.weight_audio

    # Dynamic weighting based on confidence and intensity
    if settings.dynamic_weighting:
        ct, ca = _confidence(t), _confidence(a)
        dt, da = _emotion_diversity(t), _emotion_diversity(a)

        # Boost weights based on confidence and diversity
        confidence_boost_t = ct + dt * 0.5
        confidence_boost_a = ca + da * 0.5

        # Apply intensity factor (higher intensity = trust both sources more equally)
        if intensity > 0.5:
            # High intensity: balance the sources more
            intensity_factor = intensity * 0.3
            confidence_boost_t += intensity_factor
            confidence_boost_a += intensity_factor

        wt *= (confidence_boost_t + 1e-6)
        wa *= (confidence_boost_a + 1e-6)

        s = wt + wa
        wt, wa = (wt/s, wa/s) if s > 0 else (0.5, 0.5)

    # Enhanced fusion with intensity consideration
    fused = {k: wt * t[k] + wa * a[k] for k in FACE7}

    # Apply intensity-based boost to non-neutral emotions
    if intensity > 0.3:
        for k in NON_NEUTRALS:
            if fused[k] > 0.1:  # Only boost emotions that have some presence
                fused[k] *= (1.0 + intensity * 0.5)

    # Normalize to ensure probabilities sum reasonably
    total = sum(fused.values())
    if total > 0:
        fused = {k: v/total for k, v in fused.items()}

    # === Enhanced neutral strategy ===
    strat = (settings.neutral_strategy or "ban_redistribute").lower()  # Changed default

    # More aggressive neutral handling for high-intensity cases
    if intensity > 0.4:
        if strat == "penalize":
            fused["neutral"] *= (settings.neutral_penalty * 0.5)  # Even more penalty
        else:
            strat = "ban_redistribute"  # Force redistribution for high intensity

    if strat == "penalize":
        fused["neutral"] *= settings.neutral_penalty
    elif strat == "ban_redistribute":
        fused = _redistribute_neutral(fused)
    elif strat == "ban_pick":
        # no tocamos el vector, se ignora neutral en pick_label()
        pass
    else:
        # fallback: more aggressive for high intensity
        penalty = settings.neutral_penalty
        if intensity > 0.5:
            penalty *= 0.5
        fused["neutral"] *= penalty

    return fused

def pick_label(fused: Dict[str, float]) -> str:
    strat = (settings.neutral_strategy or "ban_redistribute").lower()  # Changed default

    # Enhanced ban_pick logic
    if strat == "ban_pick":
        candidates = [(k, v) for k, v in fused.items() if k != "neutral"]
        if not candidates:
            return "surprise"  # Changed from "happy" to "surprise" for unknown cases
        return max(candidates, key=lambda kv: kv[1])[0]

    # Enhanced preference for non-neutral emotions
    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    top_label, top_score = ordered[0]

    # More aggressive non-neutral preference
    if settings.prefer_non_neutral and top_label == "neutral":
        # Look at top 3 alternatives instead of just next one
        for lab, sc in ordered[1:4]:  # Check top 3 alternatives
            if lab != "neutral":
                # More lenient thresholds for preferring non-neutral
                min_threshold = max(settings.non_neutral_min * 0.5, 0.05)  # Lower threshold
                max_margin = settings.neutral_margin * 1.5  # Larger margin

                if sc >= min_threshold and (top_score - sc) <= max_margin:
                    return lab

    return top_label
