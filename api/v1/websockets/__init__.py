from fastapi import APIRouter

from .websocket import ws_router

websocket_router = APIRouter()
websocket_router.include_router(ws_router)

__all__ = ["websocket_router"]
