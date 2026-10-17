"""Vercel entrypoint for the current logbook-only product."""

from __future__ import annotations

import os
from importlib import import_module
from typing import Any

# Vercel deploys the account-based logbook. The reversible pose-analysis
# subsystem remains available to the Docker/Render deployment, but importing it
# would add MediaPipe, OpenCV, FFmpeg, object storage, and a persistent worker to
# this request-driven service.
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("VIDEO_ANALYSIS_ENABLED", "false")

app: Any = import_module("app.main").app

__all__ = ["app"]
