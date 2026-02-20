from fastapi import APIRouter

from .incidents import incident_router

incidents_router = APIRouter()

incidents_router.include_router(incident_router)
