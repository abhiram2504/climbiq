from fastapi import APIRouter

from app.api.routes import health, sessions, videos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(videos.router)
api_router.include_router(sessions.router)
