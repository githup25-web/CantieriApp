from __future__ import annotations

from dataclasses import dataclass
from typing import IO

from minio import Minio
from minio.error import S3Error

from fastapi import UploadFile
from app.core.config import get_settings


@dataclass(frozen=True)
class UploadResult:
    pdf_url: str


def _get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


async def upload_pdf_to_minio(file: UploadFile, object_name: str) -> UploadResult:
    """
    Carica un file PDF su MinIO/S3 e ritorna la URL pubblica.
    Nota: si assume che il bucket sia già creato e che l’oggetto sia accessibile via HTTP
    tramite settings.minio_public_url.
    """
    settings = get_settings()
    client = _get_minio_client()

    if not file.filename:
        raise ValueError("Missing filename")

    content_type = file.content_type or "application/pdf"

    # Upload: MinIO SDK è sincrono, ma qui leggiamo tutto il file in memoria.
    # Se vuoi evitare memoria alta, possiamo ottimizzare con streaming in un secondo step.
    data: bytes = await file.read()

    try:
        client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=object_name,
            data=IOBytes(data),
            length=len(data),
            content_type=content_type,
        )
    except S3Error as exc:
        raise RuntimeError(f"MinIO upload failed: {exc}") from exc

    pdf_url = f"{settings.minio_public_url.rstrip('/')}/{object_name.lstrip('/')}"
    return UploadResult(pdf_url=pdf_url)


class IOBytes:
    """
    Wrapper minimo per fornire un oggetto-like file byte-oriented a MinIO.
    """
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, amt: int | None = None) -> bytes:
        if self._pos >= len(self._data):
            return b""
        if amt is None:
            amt = len(self._data) - self._pos
        chunk = self._data[self._pos : self._pos + amt]
        self._pos += len(chunk)
        return chunk
