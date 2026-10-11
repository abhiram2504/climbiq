from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import UploadFile

if TYPE_CHECKING:
    from app.core.config import Settings

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
    def __init__(
        self,
        root: Path,
        max_size_bytes: int,
        *,
        backend: str = "local",
        s3_endpoint_url: str = "",
        s3_bucket: str = "",
        s3_region: str = "auto",
        s3_access_key_id: str = "",
        s3_secret_access_key: str = "",
        signed_url_seconds: int = 900,
    ) -> None:
        self.root = root.resolve()
        self.max_size_bytes = max_size_bytes
        self.backend = backend
        self.s3_bucket = s3_bucket
        self.signed_url_seconds = signed_url_seconds
        self._s3: Any | None = None
        if backend == "s3":
            import boto3

            self._s3 = boto3.client(
                "s3",
                endpoint_url=s3_endpoint_url,
                region_name=s3_region,
                aws_access_key_id=s3_access_key_id,
                aws_secret_access_key=s3_secret_access_key,
            )

    @classmethod
    def from_settings(cls, settings: Settings) -> VideoStorage:
        return cls(
            settings.video_storage_path,
            settings.max_upload_size_bytes,
            backend=settings.storage_backend,
            s3_endpoint_url=settings.s3_endpoint_url,
            s3_bucket=settings.s3_bucket,
            s3_region=settings.s3_region,
            s3_access_key_id=settings.s3_access_key_id,
            s3_secret_access_key=settings.s3_secret_access_key,
            signed_url_seconds=settings.s3_signed_url_seconds,
        )

    async def save(self, upload: UploadFile, video_id: UUID) -> tuple[str, int, str]:
        original_name = (upload.filename or "").replace("\\", "/").split("/")[-1]
        suffix = Path(original_name).suffix.lower()
        self._validate_upload(upload, suffix)
        storage_key = f"{video_id}{suffix}"

        if self.backend == "local":
            self.root.mkdir(parents=True, exist_ok=True)
            destination = self.resolve(storage_key)
            temporary = self.root / f".{video_id}.part"
            try:
                total = await self._write_validated(upload, temporary)
                os.replace(temporary, destination)
                return storage_key, total, original_name
            except Exception:
                temporary.unlink(missing_ok=True)
                destination.unlink(missing_ok=True)
                raise
            finally:
                await upload.close()

        temporary = self._temporary_path(suffix)
        try:
            total = await self._write_validated(upload, temporary)
            self._require_s3().upload_file(
                str(temporary),
                self.s3_bucket,
                storage_key,
                ExtraArgs={"ContentType": upload.content_type or "application/octet-stream"},
            )
            return storage_key, total, original_name
        finally:
            temporary.unlink(missing_ok=True)
            await upload.close()

    @contextmanager
    def materialize(self, storage_key: str) -> Iterator[Path]:
        self._validate_key(storage_key)
        if self.backend == "local":
            path = self.resolve(storage_key)
            if not path.is_file():
                raise FileNotFoundError("The stored video file is unavailable.")
            yield path
            return

        temporary = self._temporary_path(Path(storage_key).suffix)
        try:
            self._require_s3().download_file(self.s3_bucket, storage_key, str(temporary))
            yield temporary
        finally:
            temporary.unlink(missing_ok=True)

    @contextmanager
    def output(self, storage_key: str, content_type: str = "video/mp4") -> Iterator[Path]:
        self._validate_key(storage_key)
        if self.backend == "local":
            self.root.mkdir(parents=True, exist_ok=True)
            path = self.resolve(storage_key)
            try:
                yield path
            except Exception:
                path.unlink(missing_ok=True)
                raise
            return

        temporary = self._temporary_path(Path(storage_key).suffix)
        try:
            yield temporary
            self._require_s3().upload_file(
                str(temporary),
                self.s3_bucket,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
        finally:
            temporary.unlink(missing_ok=True)

    def resolve(self, storage_key: str) -> Path:
        if self.backend != "local":
            raise RuntimeError("S3 objects must be materialized before local processing.")
        self._validate_key(storage_key)
        path = (self.root / storage_key).resolve()
        if path.parent != self.root:
            raise InvalidVideoError("Stored video path is invalid.")
        return path

    def signed_url(self, storage_key: str) -> str | None:
        self._validate_key(storage_key)
        if self.backend == "local":
            return None
        return str(
            self._require_s3().generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": storage_key},
                ExpiresIn=self.signed_url_seconds,
            )
        )

    def delete(self, storage_key: str) -> None:
        self._validate_key(storage_key)
        if self.backend == "local":
            self.resolve(storage_key).unlink(missing_ok=True)
            return
        self._require_s3().delete_object(Bucket=self.s3_bucket, Key=storage_key)

    async def _write_validated(self, upload: UploadFile, destination: Path) -> int:
        total = 0
        header = b""
        with destination.open("wb") as output:
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
        return total

    @staticmethod
    def _validate_upload(upload: UploadFile, suffix: str) -> None:
        if suffix not in ALLOWED_EXTENSIONS:
            raise InvalidVideoError("Only MP4 and MOV video files are supported.")
        if upload.content_type and upload.content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise InvalidVideoError(
                "The uploaded file does not have a supported video content type."
            )

    @staticmethod
    def _validate_key(storage_key: str) -> None:
        path = PurePosixPath(storage_key)
        if not storage_key or path.name != storage_key or storage_key in {".", ".."}:
            raise InvalidVideoError("Stored video path is invalid.")

    @staticmethod
    def _temporary_path(suffix: str) -> Path:
        descriptor, name = tempfile.mkstemp(prefix="climbiq-", suffix=suffix)
        os.close(descriptor)
        return Path(name)

    def _require_s3(self) -> Any:
        if self._s3 is None:
            raise RuntimeError("S3 storage is not configured.")
        return self._s3
