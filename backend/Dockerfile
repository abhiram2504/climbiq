FROM python:3.12-slim

ARG POSE_MODEL_URL=https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task
ARG POSE_MODEL_SHA256=5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libegl1 \
        libgl1 \
        libgles2 \
        libglib2.0-0 \
        libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.docker.md ./
RUN python -m pip install --upgrade pip && python -m pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN mkdir -p /app/data/videos /app/models \
    && curl --fail --location --silent --show-error "$POSE_MODEL_URL" --output /app/models/pose_landmarker_full.task \
    && echo "$POSE_MODEL_SHA256  /app/models/pose_landmarker_full.task" | sha256sum --check --strict

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
