# app/face_server.py
"""
Servidor dedicado para face detection (YOLOv8)
Puerto 8000 - Solo endpoints de face detection para mejor rendimiento
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.health import router as health_router
from app.routers.pepper_state import router as pepper_router
from app.logstream import router as log_router, setup_logging

# Solo importar el router de face detection
from app.routers.face_only import router as face_router
from app.routers.fusion import router as fusion_router

app = FastAPI(title="Face Emotion API", version="1.0.0", description="Dedicated server for face emotion detection")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajusta en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="👤 [FACE-SERVER] %(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)

# Logger específico para face detection
face_logger = logging.getLogger("face-detection")
face_logger.setLevel(logging.INFO)

setup_logging()

# Solo incluir routers relacionados con face detection
app.include_router(health_router)
app.include_router(face_router)
app.include_router(fusion_router)  # Fusion endpoint
app.include_router(pepper_router)
app.include_router(log_router, tags=["logs"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)