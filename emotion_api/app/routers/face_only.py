# app/routers/face_only.py
"""
Router dedicado solo para face detection (YOLOv8)
Separado del audio para evitar contención de recursos
"""
from __future__ import annotations

import io
import cv2
import numpy as np
import logging

from PIL import Image
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

# ---- Modelo YOLOv8 para emociones faciales ----
from app.routers.services.yolov8_face_emotion import classify_face_emotion_yolov8
from app.state import get_emotion_buffer

router = APIRouter(prefix="/emotion", tags=["face-emotion"])
logger = logging.getLogger("face-emotion")


# =============================================================================
# ENDPOINT: Emoción desde FRAME (imagen) para el front (YOLOv8)
# =============================================================================

@router.post("/from-frame")
async def emotion_from_frame(
    image: UploadFile = File(...),
    size: int = Form(0),     # ← ya no se usa; el wrapper decide
    room: str | None = Form(None),
):
    """
    Recibe un frame (imagen) y devuelve la emoción facial usando el modelo YOLOv8.
    Servidor dedicado para face detection únicamente.
    Respuesta:
      {
        "label": "happy",
        "scores": [{"label":"happy","score":0.92}, ...],
        "room": "test",
        "size": 640
      }
    """
    try:
        # 1) Log incoming request
        img_size = len(await image.read()) if hasattr(image, 'read') else 0
        await image.seek(0)  # Reset for actual reading
        logger.info(f"👤 [FACE] New frame received: {image.filename} (size: {img_size} bytes) in room {room}")

        # 2) bytes -> PIL -> numpy BGR
        raw = await image.read()
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
        img_bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

        actual_size = size if size > 0 else 640
        logger.info(f"👤 [FACE] 🚀 Starting YOLOv8 detection on {img_bgr.shape} image (processing size: {actual_size})")

        # 3) YOLOv8 model prediction
        result = classify_face_emotion_yolov8(img_bgr, size=actual_size)
        logger.info(f"👤 [FACE] ✅ YOLOv8 detection completed: {result}")

        # 4) Extract results from YOLOv8 response
        label = result.get("label", "neutral")
        score = result.get("score", 0.0)
        scores = result.get("scores", [{"label": label, "score": score}])
        debug_info = result.get("debug", {})

        # 5) Log detailed results
        if scores and len(scores) > 1:
            # Mostrar todas las emociones detectadas
            all_emotions = ", ".join([f"{s['label']}({s['score']:.2f})" for s in scores[:5]])
            logger.info(f"👤 [FACE] 📊 All emotions: {all_emotions}")

        logger.info(f"👤 [FACE] 🎯 Final result: {label} ({score:.3f}) | detections: {debug_info.get('total_detections', 0)} in room {room}")

        # 5) Guardar en buffer para fusión
        response_data = {
            "label": label,
            "score": score,
            "scores": scores,
            "room": room,
            "size": size,
            "debug": debug_info
        }

        if room:
            buffer = get_emotion_buffer()
            buffer.add_face(room, response_data.copy())
            logger.debug(f"👤 [FACE] Saved to buffer for room {room}")

        # 6) Return YOLOv8 response format
        return response_data

    except Exception as e:
        logger.exception("from-frame failed: %s", e)
        raise HTTPException(
            status_code=500, detail=f"from-frame failed: {type(e).__name__}: {e}"
        )