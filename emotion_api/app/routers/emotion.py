# app/routers/emotion.py
import os
import uuid
import tempfile
from subprocess import run, PIPE, CalledProcessError

import aiofiles
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException

from ..deps import (
    get_asr_model,
    get_text_emotion_pipeline,
    get_audio_emotion_pipeline,
)
from ..services.asr_whisper import transcribe_audio_file
from ..services.nlp_text_emotion import classify_text_emotions
from ..services.ser_audio_emotion import classify_audio_emotions
from ..services.fusion import fuse, pick_label
from ..services.mapping import map_to_face7
from ..services.pepper_client import send_emotion_to_pepper
from ..models.schemas import EmotionResponse, EmotionScore, PepperAck

router = APIRouter(prefix="/emotion", tags=["emotion"])


def _convert_to_wav16k(src_path: str) -> str:
    """
    Convierte cualquier audio a WAV mono 16k para el pipeline de SER.
    Usa subprocess con lista de args (robusto en Windows/Linux/Mac).
    """
    dst_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        src_path,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        dst_path,
    ]
    try:
        run(cmd, check=True, stdout=PIPE, stderr=PIPE)
    except CalledProcessError as e:
        raise HTTPException(
            status_code=400,
            detail=f"ffmpeg conversion failed: {e.stderr.decode(errors='ignore')[:300]}",
        )
    return dst_path


@router.post("/from-audio")
async def emotion_from_audio(
    audio: UploadFile = File(...),
    asr_model=Depends(get_asr_model),
    text_pipe=Depends(get_text_emotion_pipeline),
    audio_pipe=Depends(get_audio_emotion_pipeline),
):
    """
    1) Guarda el archivo subido (async, en chunks)
    2) Convierte a WAV 16k mono para SER
    3) ASR con Whisper sobre el archivo original (acepta varios formatos)
    4) NLP (texto→emoción) + SER (audio→emoción)
    5) Fusión + mapeo a FACE7
    6) Envía emoción a Pepper
    """
    raw_path = wav16_path = None
    try:
        # 1) Guardar archivo subido de forma asíncrona
        suffix = os.path.splitext(audio.filename or "")[1] or ".bin"
        raw_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{suffix}")
        async with aiofiles.open(raw_path, "wb") as f:
            while True:
                chunk = await audio.read(1024 * 1024)  # 1 MiB
                if not chunk:
                    break
                await f.write(chunk)

        # 2) Normalizar a WAV 16k mono para SER
        wav16_path = _convert_to_wav16k(raw_path)

        # 3) ASR (Whisper) — si falla con el original, intenta con el wav16
        try:
            transcript = transcribe_audio_file(asr_model, raw_path)
        except Exception:
            transcript = transcribe_audio_file(asr_model, wav16_path)

        # 4) Emoción por texto y por audio
        text_emotions = classify_text_emotions(text_pipe, transcript)
        audio_emotions = classify_audio_emotions(audio_pipe, wav16_path)

        # 5) Fusión + mapeo FACE7
        fused = fuse(text_emotions, audio_emotions)
        fused_label = pick_label(fused)
        mapped = map_to_face7(fused_label)

        # 6) Envío a Pepper
        ok = send_emotion_to_pepper(mapped)

        return {
            "result": EmotionResponse(
                transcript=transcript,
                text_emotions=[EmotionScore(**e) for e in text_emotions],
                audio_emotions=[EmotionScore(**e) for e in audio_emotions],
                fused=EmotionScore(label=fused_label, score=fused[fused_label]),
                mapped_emotion=mapped,
            ).model_dump(),
            "pepper": PepperAck(ok=ok, sent_to="pepper").model_dump(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"processing failed: {type(e).__name__}: {e}"
        )
    finally:
        # Limpieza de temporales
        for p in (raw_path, wav16_path):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
