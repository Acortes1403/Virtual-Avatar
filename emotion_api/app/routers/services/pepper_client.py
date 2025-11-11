# app/services/pepper_client.py
from typing import Optional, Dict, Any
import requests
import logging
from app.config import settings
from app.state import get_pepper_state

logger = logging.getLogger("pepper_client")

def send_emotion_to_pepper(
    mapped_emotion: str,
    room: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    timeout: float = 2.5,
) -> bool:
    """
    Envía la emoción al endpoint de Pepper.
    - Marca Pepper como ocupado (proce=0) antes de enviar
    - room: opcional, si tu proxy/bridge lo usa para enrutar
    - extra: dict opcional para campos adicionales (p.ej. intensidad, r, etc.)
    """
    state = get_pepper_state()

    # Check if Pepper is available before sending
    if not state.is_pepper_available(room):
        logger.warning(f"Pepper is BUSY, skipping {mapped_emotion} script (room: {room})")
        return False

    # Mark Pepper as busy BEFORE sending the script
    logger.info(f"Marking Pepper as BUSY before sending {mapped_emotion} script")
    state.set_busy(emotion=mapped_emotion, room=room)

    payload: Dict[str, Any] = {"emotion": mapped_emotion}
    if room:
        payload["room"] = room
    if extra:
        payload.update(extra)

    try:
        logger.info(f"Sending {mapped_emotion} script to Pepper (room: {room})")
        r = requests.post(settings.pepper_emotion_endpoint, json=payload, timeout=timeout)
        r.raise_for_status()  # lanza error si 4xx/5xx

        logger.info(f"Script {mapped_emotion} sent successfully to Pepper")
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to send {mapped_emotion} script to Pepper: {e}")

        # If sending failed, mark Pepper as available again
        logger.info("Script sending failed, marking Pepper as AVAILABLE again")
        state.set_available(room=room)
        return False
