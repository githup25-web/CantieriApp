"""Route Motor per le Presenze di cantiere (schema PASSO 1)."""

from fastapi import APIRouter, HTTPException, status

from backend.schemas.presenza_schema import (
    PresenzaCheckoutSchema,
    PresenzaCreateSchema,
    PresenzaResponseSchema,
)
from backend.services import presenza_service

router = APIRouter(prefix="/presenze", tags=["presenze"])


@router.post(
    "/checkin",
    response_model=PresenzaResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def checkin(payload: PresenzaCreateSchema) -> PresenzaResponseSchema:
    """Registra il check-in di un worker in un cantiere."""

    presenza = await presenza_service.checkin(payload)
    return PresenzaResponseSchema(**presenza.model_dump())


@router.post("/checkout", response_model=PresenzaResponseSchema)
async def checkout(payload: PresenzaCheckoutSchema) -> PresenzaResponseSchema:
    """Chiude la presenza aperta più recente di un worker in un cantiere."""

    presenza = await presenza_service.checkout(payload)
    if presenza is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessuna presenza aperta trovata per questo worker nel cantiere",
        )
    return PresenzaResponseSchema(**presenza.model_dump())


@router.get("/by-cantiere/{cantiere_id}", response_model=list[PresenzaResponseSchema])
async def list_presenze_by_cantiere(cantiere_id: str) -> list[PresenzaResponseSchema]:
    """Elenca le presenze di un cantiere, dalla più recente."""

    presenze = await presenza_service.get_by_cantiere(cantiere_id)
    return [PresenzaResponseSchema(**presenza.model_dump()) for presenza in presenze]
