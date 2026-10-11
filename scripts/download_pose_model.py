#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
MODEL_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DESTINATION = REPOSITORY_ROOT / "backend/models/pose_landmarker_full.task"


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=DESTINATION.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            with urllib.request.urlopen(MODEL_URL, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)

        digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
        if digest != MODEL_SHA256:
            raise RuntimeError(
                f"Pose model checksum mismatch: expected {MODEL_SHA256}, received {digest}"
            )
        os.replace(temporary_path, DESTINATION)
        print(f"Pose model ready at {DESTINATION}")
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
