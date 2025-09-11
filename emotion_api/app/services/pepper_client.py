import requests
from ..config import settings

def send_emotion_to_pepper(mapped_emotion: str) -> bool:
    try:
        r = requests.post(settings.pepper_emotion_endpoint, json={"emotion": mapped_emotion}, timeout=2.5)
        return r.ok
    except Exception:
        return False
