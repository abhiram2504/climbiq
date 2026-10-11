from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.services.video_storage import VideoStorage


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.content_types: dict[tuple[str, str], str] = {}

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        ExtraArgs: dict[str, str],
    ) -> None:
        object_id = (bucket, key)
        self.objects[object_id] = Path(filename).read_bytes()
        self.content_types[object_id] = ExtraArgs["ContentType"]

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        Path(filename).write_bytes(self.objects[(bucket, key)])

    def generate_presigned_url(
        self,
        operation: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        assert operation == "get_object"
        return f"https://signed.example/{Params['Bucket']}/{Params['Key']}?ttl={ExpiresIn}"

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop((Bucket, Key), None)


def fake_mp4() -> bytes:
    return b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + (b"\x00" * 32)


def test_s3_storage_upload_materialize_output_sign_and_delete(tmp_path, monkeypatch) -> None:
    fake_s3 = FakeS3Client()
    monkeypatch.setattr("boto3.client", lambda *args, **kwargs: fake_s3)
    storage = VideoStorage(
        tmp_path,
        1_000_000,
        backend="s3",
        s3_endpoint_url="https://account.r2.cloudflarestorage.com",
        s3_bucket="videos",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
        signed_url_seconds=600,
    )
    video_id = uuid4()
    upload = UploadFile(
        filename="attempt.mp4",
        file=BytesIO(fake_mp4()),
        headers=Headers({"content-type": "video/mp4"}),
    )

    storage_key, size, original_name = asyncio.run(storage.save(upload, video_id))

    assert storage_key == f"{video_id}.mp4"
    assert size == len(fake_mp4())
    assert original_name == "attempt.mp4"
    assert fake_s3.objects[("videos", storage_key)] == fake_mp4()
    assert fake_s3.content_types[("videos", storage_key)] == "video/mp4"

    with storage.materialize(storage_key) as local_copy:
        assert local_copy.read_bytes() == fake_mp4()
        materialized_path = local_copy
    assert not materialized_path.exists()

    with storage.output("annotated.mp4") as output:
        output.write_bytes(b"annotated")
    assert fake_s3.objects[("videos", "annotated.mp4")] == b"annotated"
    assert storage.signed_url(storage_key) == (
        f"https://signed.example/videos/{storage_key}?ttl=600"
    )

    storage.delete(storage_key)
    assert ("videos", storage_key) not in fake_s3.objects
