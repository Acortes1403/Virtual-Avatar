# app/services/mapping.py

# ========= FACE7: mapeo para fusión/Pepper =========
# Añadimos las identidades (passthrough) de las 7 canónicas.
NORMALIZE = {
    # Passthroughs FACE7
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "surprised": "surprised",
    "fearful": "fearful",
    "disgusted": "disgusted",
    "neutral": "neutral",

    # Sinónimos → FACE7
    "joy": "happy", "happiness": "happy", "contentment": "happy", "love": "happy", "admiration": "happy",
    "sadness": "sad", "melancholy": "sad",
    "anger": "angry", "annoyance": "angry", "frustration": "angry",
    "surprise": "surprised", "ps": "surprised",  # LSTM TESS: pleasant surprise → surprised
    "fear": "fearful", "anxiety": "fearful", "scared": "fearful",
    "disgust": "disgusted", "contempt": "disgusted",
    "calm": "neutral", "unknown": "neutral",
}

# Short-codes SER → FACE7
SHORT_TO_FACE7 = {
    "hap": "happy",
    "ang": "angry",
    "sad": "sad",
    "neu": "neutral",
    "sur": "surprised",
    "fea": "fearful",
    "dis": "disgusted",
}

FACE7 = {"happy", "sad", "angry", "surprised", "fearful", "disgusted", "neutral"}

def map_to_face7(label: str) -> str:
    if not label:
        return "neutral"
    lab = label.lower().strip()
    if lab in SHORT_TO_FACE7:
        return SHORT_TO_FACE7[lab]
    return NORMALIZE.get(lab, "neutral")


# ========= TEXT7: para homogeneizar vista de audio/texto =========
TEXT7 = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]

# Short-codes SER → TEXT7
SHORT_TO_TEXT7 = {
    "hap": "joy",
    "ang": "anger",
    "sad": "sadness",
    "neu": "neutral",
    "sur": "surprise",
    "fea": "fear",
    "dis": "disgust",
}

# Sinónimos y FACE7 → TEXT7
NORM_TO_TEXT7 = {
    # Passthroughs TEXT7
    "anger": "anger", "disgust": "disgust", "fear": "fear",
    "joy": "joy", "neutral": "neutral", "sadness": "sadness", "surprise": "surprise",

    # FACE7 → TEXT7
    "happy": "joy",
    "sad": "sadness",
    "angry": "anger",
    "surprised": "surprise",
    "fearful": "fear",
    "disgusted": "disgust",

    # Sinónimos → TEXT7
    "happiness": "joy", "contentment": "joy", "love": "joy", "admiration": "joy",
    "melancholy": "sadness",
    "annoyance": "anger", "frustration": "anger",
    "anxiety": "fear", "scared": "fear",
    "contempt": "disgust",
    "calm": "neutral", "unknown": "neutral",
}

def map_to_text7(label: str) -> str:
    if not label:
        return "neutral"
    lab = label.lower().strip()
    if lab in SHORT_TO_TEXT7:
        return SHORT_TO_TEXT7[lab]
    return NORM_TO_TEXT7.get(lab, "neutral")

FACE7_TO_VA = {
    "neutral":   ( 0.00,  0.00),
    "happy":     ( 0.70,  0.60),
    "surprised": ( 0.20,  0.80),
    "angry":     (-0.70,  0.70),
    "fearful":   (-0.70,  0.60),
    "disgusted": (-0.60,  0.30),
    "sad":       (-0.70, -0.40),
}
