# app/routers/health.py
from fastapi import APIRouter
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health():
    return {"ok": True}

@router.get("/config")
def show_config():
    return settings.model_dump()
