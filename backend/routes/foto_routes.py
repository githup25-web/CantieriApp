"""Route Motor per le Foto di Avanzamento (schema PASSO 1)."""

from fastapi import APIRouter, File, Form, UploadFile, status

from backend.schemas.foto_schema import (
    FotoAvanzamentoCreateSchema,
    FotoAvanzamentoResponseSchema,
)
from backend.services import foto_service

router = APIRouter(prefix="/foto", tags=["foto-avanzamento"])


@router.post(
    "/upload",
    response_model=FotoAvanzamentoResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_foto(
    cantiere_id: str = Form(...),
    worker_id: str = Form(...),
    descrizione: str | None = Form(default=None),
    file: UploadFile = File(...),
) -> FotoAvanzamentoResponseSchema:
    """Carica una foto di avanzamento (multipart) per un cantiere."""

    url = await foto_service.save_upload_file(file)
    payload = FotoAvanzamentoCreateSchema(
        cantiere_id=cantiere_id,
        worker_id=worker_id,
        url=url,
        descrizione=descrizione,
    )
    foto = await foto_service.create(payload)
    return FotoAvanzamentoResponseSchema(**foto.model_dump())


@router.get("/by-cantiere/{cantiere_id}", response_model=list[FotoAvanzamentoResponseSchema])
async def list_foto_by_cantiere(cantiere_id: str) -> list[FotoAvanzamentoResponseSchema]:
    """Elenca le foto di avanzamento di un cantiere."""

    foto_list = await foto_service.get_by_cantiere(cantiere_id)
    return [FotoAvanzamentoResponseSchema(**foto.model_dump()) for foto in foto_list]
