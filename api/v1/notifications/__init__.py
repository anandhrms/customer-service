from fastapi import APIRouter

from .notifications import notifications_router

notification_router = APIRouter()

notification_router.include_router(notifications_router)
