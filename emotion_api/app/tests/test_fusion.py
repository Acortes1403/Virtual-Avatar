from app.deps import get_text_emotion_pipeline, get_audio_emotion_pipeline
from app.services.nlp_text_emotion import classify_text_emotions
from app.services.ser_audio_emotion import classify_audio_emotions
from app.services.fusion import fuse, argmax

if __name__ == "__main__":
    text_pipe = get_text_emotion_pipeline()
    audio_pipe = get_audio_emotion_pipeline()

    transcript = "I am not okay, I'm angry about this"
    text_scores = classify_text_emotions(text_pipe, transcript)
    audio_scores = classify_audio_emotions(audio_pipe, "sample.wav")

    fused = fuse(text_scores, audio_scores)
    print("FUSED:", fused, "→ winner:", argmax(fused))
