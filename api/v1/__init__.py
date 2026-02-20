from fastapi import APIRouter

from .blacklists_customer import blacklists_router
from .cameras import cameras_router
from .customers import customers_router
from .evidences import evidences_router
from .firebase import firebase_router
from .incidents import incidents_router
from .monitoring import monitoring_router
from .notifications import notification_router
from .websockets import websocket_router

v1_router = APIRouter()
v1_router.include_router(monitoring_router, prefix="/monitoring")
v1_router.include_router(incidents_router, prefix="/incidents")
v1_router.include_router(blacklists_router, prefix="/blacklists")
v1_router.include_router(firebase_router, prefix="/firebase")
v1_router.include_router(cameras_router, prefix="/cameras")
v1_router.include_router(customers_router, prefix="/customers")
v1_router.include_router(notification_router, prefix="/notifications")
v1_router.include_router(websocket_router)
v1_router.include_router(evidences_router, prefix="/evidences")
