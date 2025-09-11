from app.deps import get_text_emotion_pipeline
from app.services.nlp_text_emotion import classify_text_emotions

if __name__ == "__main__":
    nlp = get_text_emotion_pipeline()
    samples = [
        "I'm very happy today!",
        "Esto me frustra demasiado.",
        "I feel sad about this.",
        "That was shocking!"
    ]
    for s in samples:
        scores = classify_text_emotions(nlp, s)
        top = sorted(scores, key=lambda x: x["score"], reverse=True)[:2]
        print(s, "->", top)
