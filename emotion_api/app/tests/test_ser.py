from app.deps import get_audio_emotion_pipeline
from app.services.ser_audio_emotion import classify_audio_emotions

if __name__ == "__main__":
    pipe = get_audio_emotion_pipeline()
    scores = classify_audio_emotions(pipe, "sample.wav")  # usa tu sample.wav
    top = sorted(scores, key=lambda x: x["score"], reverse=True)[:3]
    print("SER ->", top)
