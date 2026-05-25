from fastapi import APIRouter

from app.api.routes.google_oauth import router as google_oauth_router
from app.api.routes.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(google_oauth_router)
api_router.include_router(health_router)
