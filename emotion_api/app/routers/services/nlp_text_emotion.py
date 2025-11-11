# app/routers/services/nlp_text_emotion.py
from typing import Any, List, Dict, TypedDict
import re

# TypedDict con la forma final esperada
class EmotionProb(TypedDict):
    label: str
    score: float

def _to_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0

def _preprocess_text(text: str) -> str:
    """Preprocess text to improve emotion detection."""
    if not text:
        return text

    # Normalize multiple repetitions of words (more than 3 consecutive)
    # "wait wait wait wait wait" -> "wait wait wait"
    text = re.sub(r'\b(\w+)(\s+\1){3,}', r'\1 \1 \1', text, flags=re.IGNORECASE)

    # Add punctuation to indicate urgency for repeated words
    text = re.sub(r'\b(\w+)(\s+\1){2,}', r'\1! \1! \1!', text, flags=re.IGNORECASE)

    return text.strip()

def _analyze_text_patterns(text: str) -> List[EmotionProb]:
    """Analyze text patterns for emotion cues that ML models might miss."""
    text_lower = text.lower()
    pattern_emotions = []

    # Pattern-based emotion detection for common cases
    patterns = {
        'fear': {
            'patterns': [
                r'\b(no\s+){3,}',  # "no no no no"
                r'\b(wait\s+){3,}',  # "wait wait wait"
                r'\b(stop\s+){2,}',  # "stop stop stop"
                r'\b(help\s+){2,}',  # "help help help"
            ],
            'weight': 0.7
        },
        'surprise': {
            'patterns': [
                r'\b(what\s+){2,}',  # "what what what"
                r'\b(oh\s+){2,}',    # "oh oh oh"
                r'\bwow+\b',         # "wow", "woww"
            ],
            'weight': 0.6
        },
        'anger': {
            'patterns': [
                r'\b(damn\s+){2,}',  # "damn damn damn"
                r'\b(shit\s+){2,}',  # repeated curse words
                r'\b(fuck\s+){2,}',
            ],
            'weight': 0.8
        }
    }

    for emotion, config in patterns.items():
        for pattern in config['patterns']:
            if re.search(pattern, text_lower):
                pattern_emotions.append({
                    "label": emotion,
                    "score": config['weight']
                })
                break  # One match per emotion is enough

    return pattern_emotions

def classify_text_emotions(nlp_pipe: Any, text: str) -> List[EmotionProb]:
    """
    Enhanced text emotion classification with preprocessing and pattern detection.
    """
    if not text or not text.strip():
        return [{"label": "neutral", "score": 1.0}]

    # Preprocess text for better emotion detection
    processed_text = _preprocess_text(text)

    # Get pattern-based emotions first
    pattern_emotions = _analyze_text_patterns(text)

    # Get ML model predictions
    try:
        raw = nlp_pipe(processed_text)
    except Exception:
        # Fallback to original text if preprocessing fails
        try:
            raw = nlp_pipe(text)
        except Exception:
            raw = []

    # Normalize ML model output
    ml_emotions: List[EmotionProb] = []
    if isinstance(raw, dict):
        raw = [raw]
    if isinstance(raw, list):
        for e in raw:
            if not isinstance(e, dict):
                continue
            lab = str(e.get("label", "")).strip().lower()
            if not lab:
                continue

            # Map some common label variations
            label_mapping = {
                'joy': 'happy',
                'sadness': 'sad',
                'anger': 'angry',
                'disgust': 'disgusted'
            }
            lab = label_mapping.get(lab, lab)

            ml_emotions.append({"label": lab, "score": _to_float(e.get("score", 0.0))})

    # Combine pattern-based and ML-based emotions
    combined_emotions = {}

    # Add ML emotions (but don't let neutral dominate if we have patterns)
    for emotion in ml_emotions:
        label = emotion["label"]
        score = emotion["score"]

        # If we have pattern-based emotions and this is neutral, reduce its influence
        if pattern_emotions and label == "neutral":
            score *= 0.3  # Reduce neutral influence when patterns exist

        combined_emotions[label] = score

    # Boost with pattern-based emotions (but don't completely override ML)
    for emotion in pattern_emotions:
        label = emotion["label"]
        pattern_score = emotion["score"]

        if label in combined_emotions:
            # Combine pattern and ML predictions more balanced
            original_score = combined_emotions[label]
            combined_emotions[label] = min(1.0, original_score * 0.5 + pattern_score * 0.5)
        else:
            # Add new emotion from pattern (but at reduced confidence)
            combined_emotions[label] = pattern_score * 0.8

    # If no ML emotions detected, ensure we have a baseline
    if not ml_emotions:
        if not combined_emotions:
            combined_emotions = {"neutral": 0.5}

    # Convert back to list format
    result = [{"label": label, "score": score} for label, score in combined_emotions.items()]

    if not result:
        result = [{"label": "neutral", "score": 1.0}]

    # Sort by score (highest first)
    result.sort(key=lambda x: x["score"], reverse=True)

    return result
