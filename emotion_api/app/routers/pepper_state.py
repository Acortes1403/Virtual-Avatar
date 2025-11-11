# app/routers/pepper_state.py
"""
Pepper state management endpoints
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Form
from typing import Optional

from app.state import get_pepper_state

router = APIRouter(prefix="/pepper", tags=["pepper"])
logger = logging.getLogger("pepper_state")

@router.get("/status")
def get_pepper_status(room: Optional[str] = None):
    """
    Get current Pepper process status

    Returns:
        {
            "proce": 1,  // 1 = available, 0 = busy
            "available": true,
            "room": "test"
        }
    """
    state = get_pepper_state()
    proce = state.get_proce(room)

    return {
        "proce": proce,
        "available": proce == 1,
        "busy": proce == 0,
        "room": room,
        "full_state": state.get_full_state()
    }

@router.post("/set-busy")
async def set_pepper_busy(
    emotion: Optional[str] = Form(None),
    room: Optional[str] = Form(None)
):
    """
    Mark Pepper as busy (proce = 0)
    Usually called when sending a script to Pepper
    """
    state = get_pepper_state()
    success = state.set_busy(emotion=emotion, room=room)

    logger.info(f"Pepper marked as BUSY - emotion: {emotion}, room: {room}")

    return {
        "success": success,
        "proce": 0,
        "message": f"Pepper is now BUSY executing {emotion} script",
        "room": room
    }

@router.post("/set-available")
async def set_pepper_available(room: Optional[str] = Form(None)):
    """
    Mark Pepper as available (proce = 1)
    Called by Pepper proxy when script execution completes
    """
    state = get_pepper_state()
    success = state.set_available(room=room)

    logger.info(f"Pepper marked as AVAILABLE - room: {room}")

    return {
        "success": success,
        "proce": 1,
        "message": "Pepper is now AVAILABLE for new scripts",
        "room": room
    }

@router.post("/reset")
def reset_pepper_state():
    """
    Reset Pepper state to available (emergency reset)
    """
    state = get_pepper_state()
    success = state.set_available()

    logger.warning("Pepper state manually RESET to available")

    return {
        "success": success,
        "proce": 1,
        "message": "Pepper state reset to AVAILABLE"
    }