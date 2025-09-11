# app/config.py
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
import os

# Cargar .env con override para pisar variables previas del entorno
load_dotenv(find_dotenv(), override=True)

class Settings(BaseModel):
    # Endpoints / modelos
    pepper_emotion_endpoint: str = os.getenv("PEPPER_EMOTION_ENDPOINT", "http://localhost:5000/emotion")
    asr_language: str = os.getenv("ASR_LANGUAGE", "auto")
    text_emo_model: str = os.getenv("TEXT_EMO_MODEL", "j-hartmann/emotion-english-distilroberta-base")
    audio_emo_model: str = os.getenv("AUDIO_EMO_MODEL", "r-f/wav2vec-english-speech-emotion-recognition")

    # Pesos base
    weight_text: float = float(os.getenv("WEIGHT_TEXT", "0.45"))
    weight_audio: float = float(os.getenv("WEIGHT_AUDIO", "0.55"))

    # Diales anti-neutral
    neutral_penalty: float = float(os.getenv("NEUTRAL_PENALTY", "0.80"))
    prefer_non_neutral: bool = os.getenv("PREFER_NON_NEUTRAL", "true").lower() == "true"
    neutral_margin: float = float(os.getenv("NEUTRAL_MARGIN", "0.10"))
    non_neutral_min: float = float(os.getenv("NON_NEUTRAL_MIN", "0.10"))

    # Pesos dinámicos según confianza de cada canal
    dynamic_weighting: bool = os.getenv("DYNAMIC_WEIGHTING", "true").lower() == "true"

    # >>> NUEVO: estrategia para 'neutral' <<<
    # 'penalize' | 'ban_pick' | 'ban_redistribute'
    neutral_strategy: str = os.getenv("NEUTRAL_STRATEGY", "penalize")

settings = Settings()
