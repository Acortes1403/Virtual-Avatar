# app/logstream.py
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Any

from fastapi import APIRouter
from starlette.responses import StreamingResponse

# Router público (lo que importará main.py)
router = APIRouter()

# Cola global para eventos de log
LOG_QUEUE: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue(maxsize=1000)


class SSELogHandler(logging.Handler):
    """Handler que envía los logs a una cola para ser servidos vía SSE."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            evt = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            try:
                LOG_QUEUE.put_nowait(evt)
            except asyncio.QueueFull:
                try:
                    LOG_QUEUE.get_nowait()
                except Exception:
                    pass
                try:
                    LOG_QUEUE.put_nowait(evt)
                except Exception:
                    pass
        except Exception:
            # no romper en caso de error de logging
            pass


async def _event_gen() -> AsyncIterator[str]:
    """Genera eventos SSE desde la cola de logs, con keepalive periódico."""
    while True:
        try:
            evt = await asyncio.wait_for(LOG_QUEUE.get(), timeout=15.0)
            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            # Comentario SSE como keepalive (no visible para el cliente)
            yield ": keepalive\n\n"


@router.get("/logs/stream")
def stream_logs():
    """Stream de eventos de log como Server-Sent Events (SSE)."""
    return StreamingResponse(_event_gen(), media_type="text/event-stream")


def setup_logging():
    """Configura el logger 'emotion' para enviar eventos a la cola SSE."""
    sse_handler = SSELogHandler()
    sse_handler.setLevel(logging.INFO)

    emo_logger = logging.getLogger("emotion")
    emo_logger.setLevel(logging.INFO)

    # Evita duplicados cuando --reload está activo
    if not any(isinstance(h, SSELogHandler) for h in emo_logger.handlers):
        emo_logger.addHandler(sse_handler)

    # (Opcional) enganchar uvicorn si quieres ver todo:
    # for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    #     lg = logging.getLogger(name)
    #     lg.setLevel(logging.INFO)
    #     if not any(isinstance(h, SSELogHandler) for h in lg.handlers):
    #         lg.addHandler(sse_handler)
