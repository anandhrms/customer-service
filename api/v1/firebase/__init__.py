from fastapi import APIRouter

from .firestore import firestore_router

firebase_router = APIRouter()
firebase_router.include_router(firestore_router)
