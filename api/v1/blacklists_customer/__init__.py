from fastapi import APIRouter

from .blacklist_customer import blacklist_router

blacklists_router = APIRouter()

blacklists_router.include_router(blacklist_router)
