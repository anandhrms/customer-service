from fastapi import APIRouter

from .cameras import camera_router

cameras_router = APIRouter()

cameras_router.include_router(camera_router)
