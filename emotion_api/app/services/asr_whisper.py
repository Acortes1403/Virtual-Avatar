# app/services/asr_whisper.py
import whisper
from ..config import settings

def transcribe_audio_file(asr_model: whisper.Whisper, file_path: str) -> str:
    opts = {
    "language": None if settings.asr_language == "auto" else settings.asr_language,
    "temperature": 0.0,
    "best_of": 5,
    "beam_size": 5,
    "condition_on_previous_text": False,
    "fp16": False
    }

    result = asr_model.transcribe(file_path, **opts)
    return (result.get("text") or "").strip()

