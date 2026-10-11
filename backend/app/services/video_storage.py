from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

ALLOWED_EXTENSIONS = {".mp4", ".mov"}
ALLOWED_CONTENT_TYPES = {
    "application/mp4",
    "application/octet-stream",
    "video/mp4",
    "video/quicktime",
}
CHUNK_SIZE = 1024 * 1024


class InvalidVideoError(ValueError):
    pass


class UploadTooLargeError(ValueError):
    pass


class VideoStorage:
    def __init__(self, root: Path, max_size_bytes: int) -> None:
        self.root = root.resolve()
        self.max_size_bytes = max_size_bytes

    async def save(self, upload: UploadFile, video_id: UUID) -> tuple[str, int, str]:
        original_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
        suffix = Path(original_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidVideoError("Only MP4 and MOV video files are supported.")
        if upload.content_type and upload.content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise InvalidVideoError(
                "The uploaded file does not have a supported video content type."
            )

        self.root.mkdir(parents=True, exist_ok=True)
        storage_key = f"{video_id}{suffix}"
        destination = self.root / storage_key
        temporary = self.root / f".{video_id}.part"
        total = 0
        header = b""

        try:
            with temporary.open("wb") as output:
                while chunk := await upload.read(CHUNK_SIZE):
                    total += len(chunk)
                    if total > self.max_size_bytes:
                        raise UploadTooLargeError(
                            f"Video exceeds the {self.max_size_bytes // (1024 * 1024)} MB limit."
                        )
                    if len(header) < 32:
                        header += chunk[: 32 - len(header)]
                    output.write(chunk)

            if total == 0:
                raise InvalidVideoError("The uploaded video is empty.")
            if len(header) < 12 or header[4:8] != b"ftyp":
                raise InvalidVideoError("The file is not a valid MP4 or MOV container.")

            os.replace(temporary, destination)
            return storage_key, total, original_name
        except Exception:
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def resolve(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if path.parent != self.root:
            raise InvalidVideoError("Stored video path is invalid.")
        return path

    def delete(self, storage_key: str) -> None:
        self.resolve(storage_key).unlink(missing_ok=True)
