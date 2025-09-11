# app/tests/test_asr.py
from app.deps import get_asr_model
from app.services.asr_whisper import transcribe_audio_file

if __name__ == "__main__":
    model = get_asr_model()
    text = transcribe_audio_file(model, "sample.wav")  # usa un WAV cortito de prueba
    print("TRANSCRIPT:", text)

