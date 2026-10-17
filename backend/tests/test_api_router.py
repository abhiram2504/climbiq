from fastapi import FastAPI

from app.api.router import create_api_router


def test_logbook_only_router_excludes_legacy_video_routes() -> None:
    application = FastAPI()
    application.include_router(
        create_api_router(video_analysis_enabled=False),
        prefix="/api",
    )
    paths = set(application.openapi()["paths"])

    assert "/api/health" in paths
    assert "/api/logbook" in paths
    assert "/api/projects" in paths
    assert not any(path.startswith("/api/videos") for path in paths)
    assert not any(path.startswith("/api/sessions") for path in paths)
