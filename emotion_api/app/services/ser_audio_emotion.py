# app/services/ser_audio_emotion.py
from typing import List, Dict, Any
from transformers import pipeline
from .mapping import map_to_text7, TEXT7

def _flatten_output(out: Any) -> List[Dict[str, float]]:
    # normaliza salida del pipeline a una lista de {label, score}
    if isinstance(out, list):
        if out and isinstance(out[0], dict):
            return out
        if out and isinstance(out[0], list) and out[0]:
            return out[0]
    return out or []

def _infer_all_labels(audio_pipe: pipeline, file_path: str) -> List[Dict[str, float]]:
    """
    Intenta primero con top_k=None (todas las clases).
    Si por cualquier razón el modelo/pipeline devuelve menos de 7,
    reintenta con top_k=K (K = nº de labels del modelo).
    """
    # 1) intento "todas"
    raw = audio_pipe(file_path, top_k=None)
    rows = _flatten_output(raw)

    if len(rows) < 7:
        # 2) reintento con K labels explícitas
        cfg = getattr(audio_pipe.model, "config", None)
        id2label = getattr(cfg, "id2label", {}) if cfg else {}
        K = max(7, len(id2label)) or 7
        raw = audio_pipe(file_path, top_k=K)
        rows = _flatten_output(raw)

    return rows

def classify_audio_emotions(
    audio_pipe: pipeline,
    file_path: str,
    normalize: bool = False,
) -> List[Dict[str, float]]:
    rows = _infer_all_labels(audio_pipe, file_path)

    # Agregamos scores mapeados a TEXT7
    agg: Dict[str, float] = {lab: 0.0 for lab in TEXT7}
    for r in rows:
        lab = map_to_text7(str(r.get("label", "")))
        agg[lab] += float(r.get("score", 0.0))

    # normalización opcional
    if normalize:
        s = sum(agg.values())
        if s > 0:
            for k in agg:
                agg[k] = agg[k] / s

    # Siempre devolvemos las 7 etiquetas en orden fijo
    return [{"label": lab, "score": agg[lab]} for lab in TEXT7]
