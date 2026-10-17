from fastapi import APIRouter

from app.api.routes import auth, health, logbook, projects
from app.core.config import get_settings


def create_api_router(*, video_analysis_enabled: bool) -> APIRouter:
    router = APIRouter()
    router.include_router(health.router)
    router.include_router(auth.router)
    router.include_router(logbook.router)
    router.include_router(projects.router)

    if video_analysis_enabled:
        from app.api.routes import sessions, videos

        router.include_router(videos.router)
        router.include_router(sessions.router)

    return router


api_router = create_api_router(
    video_analysis_enabled=get_settings().video_analysis_enabled,
)
