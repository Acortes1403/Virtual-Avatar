from pydantic import BaseModel
from typing import List

class EmotionScore(BaseModel):
    label: str
    score: float

class EmotionResponse(BaseModel):
    transcript: str
    text_emotions: List[EmotionScore]
    audio_emotions: List[EmotionScore]
    fused: EmotionScore
    mapped_emotion: str

class PepperAck(BaseModel):
    ok: bool
    sent_to: str
