from transformers import pipeline
from typing import List, Dict

def classify_text_emotions(nlp_pipe: pipeline, text: str) -> List[Dict]:
    if not text or not text.strip():
        return [{"label": "neutral", "score": 1.0}]
    out = nlp_pipe(text)[0]  
    return [{"label": r["label"].lower(), "score": float(r["score"])} for r in out]
