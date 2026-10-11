from fastapi import APIRouter

from app.api.routes import auth, health, sessions, videos

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(videos.router)
api_router.include_router(sessions.router)
