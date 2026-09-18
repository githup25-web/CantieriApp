"""Servizio Motor per la gestione delle Foto di Avanzamento (schema PASSO 1)."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.core.database import get_collection
from backend.models.foto_avanzamento import FotoAvanzamento
from backend.schemas.foto_schema import FotoAvanzamentoCreateSchema

COLLECTION_NAME = "foto_avanzamento"
UPLOAD_DIR = Path("backend/uploads/foto")


def _collection():
    return get_collection(COLLECTION_NAME)


async def save_upload_file(file: UploadFile) -> str:
    """Salva il file multipart ricevuto su disco e restituisce l'URL relativo."""

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "").suffix
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename

    contents = await file.read()
    destination.write_bytes(contents)

    return f"/uploads/foto/{filename}"


async def create(payload: FotoAvanzamentoCreateSchema) -> FotoAvanzamento:
    """Inserisce una nuova foto di avanzamento."""

    foto = FotoAvanzamento(**payload.model_dump())
    await _collection().insert_one(foto.model_dump(by_alias=True))
    return foto


async def get_by_cantiere(cantiere_id: str) -> list[FotoAvanzamento]:
    """Elenca le foto di avanzamento di un cantiere, dalla più recente."""

    docs = (
        await _collection()
        .find({"cantiere_id": cantiere_id})
        .sort("timestamp", -1)
        .to_list(length=500)
    )
    return [FotoAvanzamento(**doc) for doc in docs]
