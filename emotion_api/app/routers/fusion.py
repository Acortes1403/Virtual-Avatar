# emotion_api/app/routers/fusion.py
"""
Endpoint para fusión de emociones (Face + Audio)
Implementa sistema de votación 2oo2 con pesos dinámicos
"""

from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any
import logging

from app.state import get_emotion_buffer
from app.routers.services.fusion_voting import get_fusion_system
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fusion", tags=["emotion-fusion"])

# Obtener instancia global del sistema de fusión
fusion_system = get_fusion_system({
    'base_audio_weight': settings.fusion_base_audio_weight,
    'base_face_weight': settings.fusion_base_face_weight,
    'weight_adjustment_mode': settings.fusion_weight_adjustment_mode,
    'min_weight': settings.fusion_min_weight,
    'max_weight': settings.fusion_max_weight,
    'min_confidence': settings.fusion_min_confidence,
    'strong_confidence': settings.fusion_strong_confidence,
    'boost_consensus': settings.fusion_boost_consensus,
    'consensus_boost': settings.fusion_consensus_boost,
    'penalize_conflict': settings.fusion_penalize_conflict,
    'conflict_penalty': settings.fusion_conflict_penalty,
    'suppress_neutral': settings.fusion_suppress_neutral,
    'neutral_threshold': settings.fusion_neutral_threshold,
    'neutral_min_gap': settings.fusion_neutral_min_gap,
    'debug_mode': settings.fusion_debug_mode,
})


@router.post("/fuse")
async def fuse_emotions(
    face_emotion: str = Form(...),
    face_confidence: float = Form(...),
    audio_emotion: str = Form(...),
    audio_confidence: float = Form(...),
    room: str = Form("default")
):
    """
    Endpoint para fusión manual (testing)

    Ejemplo:
        POST /fusion/fuse
        face_emotion=happy&face_confidence=0.85&audio_emotion=sad&audio_confidence=0.70
    """
    try:
        # Construir resultados simulados
        face_result = {
            "label": face_emotion,
            "score": face_confidence,
            "scores": [{"label": face_emotion, "score": face_confidence}]
        }

        audio_result = {
            "label": audio_emotion,
            "score": audio_confidence,
            "scores": [{"label": audio_emotion, "score": audio_confidence}]
        }

        # Fusionar
        result = fusion_system.fuse(face_result, audio_result)

        logger.info(f"[FUSION] Manual fusion for room {room}: {result['emotion']} ({result['confidence']:.2f}) via {result['strategy']}")

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"[FUSION] Error in manual fusion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-fuse")
async def auto_fuse(room: str = Form(...)):
    """
    Fusión automática usando últimas detecciones del buffer

    Requiere que se hayan hecho detecciones recientes de face y audio

    Returns:
        {
            "emotion": str,
            "confidence": float,
            "strategy": str,
            "weights": {"face": float, "audio": float},
            "face": {...},
            "audio": {...},
            "debug": {...}
        }
    """
    try:
        buffer = get_emotion_buffer()

        # Obtener últimas detecciones
        face_result = buffer.get_latest_face(room)
        audio_result = buffer.get_latest_audio(room)

        if not face_result:
            raise HTTPException(status_code=400, detail="No hay detección facial reciente para esta room")

        if not audio_result:
            raise HTTPException(status_code=400, detail="No hay detección de audio reciente para esta room")

        # Fusionar con suavizado temporal (pasar room para tracking de historial)
        result = fusion_system.fuse(face_result, audio_result, room=room)

        # Log con información temporal si está disponible
        temporal_info = result.get('temporal', {})
        temporal_flag = f" [{temporal_info.get('adjustment', 'none')}]" if temporal_info.get('adjustment') else ""

        if settings.fusion_log_all_fusions:
            logger.info(
                f"[FUSION] Auto-fusion for room {room}: {result['emotion']} "
                f"({result['confidence']:.2f}) via {result['strategy']}{temporal_flag}"
            )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[FUSION] Error in auto-fusion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buffer-stats")
def get_buffer_stats(room: str = None):
    """
    Obtiene estadísticas del buffer de emociones

    Args:
        room: Opcional, si se especifica devuelve stats de esa room
    """
    try:
        buffer = get_emotion_buffer()
        stats = buffer.get_stats(room)
        return JSONResponse(content=stats)

    except Exception as e:
        logger.error(f"[FUSION] Error getting buffer stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
def get_config():
    """
    Obtiene configuración actual del sistema de fusión
    """
    return JSONResponse(content=fusion_system.config)


@router.post("/config")
def update_config(config: Dict[str, Any]):
    """
    Actualiza configuración del sistema de fusión en caliente

    Body: JSON con parámetros a actualizar
    {
        "base_audio_weight": 0.60,
        "base_face_weight": 0.40,
        ...
    }
    """
    try:
        fusion_system.update_config(config)
        logger.info(f"[FUSION] Config updated: {config}")
        return JSONResponse(content={
            "status": "updated",
            "config": fusion_system.config
        })

    except Exception as e:
        logger.error(f"[FUSION] Error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/temporal-config")
def get_temporal_config():
    """
    Obtiene configuración actual del suavizado temporal
    """
    return JSONResponse(content=fusion_system.temporal_config)


@router.post("/temporal-config")
def update_temporal_config(config: Dict[str, Any]):
    """
    Actualiza configuración del suavizado temporal en caliente

    Body: JSON con parámetros a actualizar
    {
        "enable_smoothing": false,  // Deshabilitar temporalmente
        "enable_persistence": false,  // Deshabilitar persistencia
        "min_emotion_duration_sec": 0.5,  // Reducir tiempo mínimo
        ...
    }
    """
    try:
        fusion_system.temporal_config.update(config)
        logger.info(f"[FUSION] Temporal config updated: {config}")
        return JSONResponse(content={
            "status": "updated",
            "temporal_config": fusion_system.temporal_config
        })

    except Exception as e:
        logger.error(f"[FUSION] Error updating temporal config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{room}")
def get_fusion_history(room: str):
    """
    Obtiene el historial de fusiones de una room (para debug)
    """
    try:
        history = fusion_system.fusion_history.get(room, [])
        persistence = fusion_system.persistence_systems.get(room, None)

        result = {
            "room": room,
            "history": history,
            "history_size": len(history),
        }

        if persistence:
            result["persistence"] = {
                "last_strong_emotion": persistence.last_strong_emotion,
                "last_strong_confidence": persistence.last_strong_confidence,
            }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"[FUSION] Error getting history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-buffer")
async def clear_buffer(room: str = Form(None)):
    """
    Limpia el buffer de emociones Y el historial de fusión

    Args:
        room: Opcional, si se especifica limpia solo esa room, sino limpia todo
    """
    try:
        buffer = get_emotion_buffer()

        if room:
            buffer.clear_room(room)
            fusion_system.clear_room_history(room)
            message = f"Buffer AND fusion history cleared for room: {room}"
        else:
            buffer.clear_all()
            # Limpiar historial de todas las rooms
            for room_id in list(fusion_system.fusion_history.keys()):
                fusion_system.clear_room_history(room_id)
            message = "All buffers AND fusion history cleared"

        logger.info(f"[FUSION] {message}")
        return JSONResponse(content={"status": "success", "message": message})

    except Exception as e:
        logger.error(f"[FUSION] Error clearing buffer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
