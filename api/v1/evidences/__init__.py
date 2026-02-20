from fastapi import APIRouter

from .evidences import evidence_router

evidences_router = APIRouter()

evidences_router.include_router(evidence_router, tags=["Evidences"])
