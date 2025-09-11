# app/deps.py
from functools import lru_cache
from transformers import pipeline
import whisper
from .config import settings

@lru_cache(maxsize=1)
def get_asr_model():
    # Cambia "base" por "tiny"/"small" si quieres más velocidad
    return whisper.load_model("base")

@lru_cache(maxsize=1)
def get_text_emotion_pipeline():
    # return_all_scores=True para obtener todas las probabilidades
    return pipeline("text-classification", model=settings.text_emo_model, return_all_scores=True)

# --- Cambios aquí ---
# app/deps.py (solo este fragmento)
@lru_cache(maxsize=1)
def _audio_pipe_cached(model_name: str):
    # sin top_k aquí
    return pipeline("audio-classification", model=model_name)

def get_audio_emotion_pipeline():
    return _audio_pipe_cached(settings.audio_emo_model)

