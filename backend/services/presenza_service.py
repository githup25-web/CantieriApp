"""Servizio Motor per la gestione delle Presenze di cantiere (schema PASSO 1)."""

from datetime import datetime, timezone

from pymongo import ReturnDocument

from backend.core.database import get_collection
from backend.models.presenza import Presenza
from backend.schemas.presenza_schema import PresenzaCheckoutSchema, PresenzaCreateSchema

COLLECTION_NAME = "presenze"


def _collection():
    return get_collection(COLLECTION_NAME)


async def create(payload: PresenzaCreateSchema) -> Presenza:
    """Inserisce una nuova presenza."""

    presenza = Presenza(**payload.model_dump())
    await _collection().insert_one(presenza.model_dump(by_alias=True))
    return presenza


async def get_by_cantiere(cantiere_id: str) -> list[Presenza]:
    """Elenca le presenze di un cantiere, dalla più recente."""

    docs = (
        await _collection()
        .find({"cantiere_id": cantiere_id})
        .sort("checkin", -1)
        .to_list(length=500)
    )
    return [Presenza(**doc) for doc in docs]


async def checkin(payload: PresenzaCreateSchema) -> Presenza:
    """Registra il check-in di un worker in un cantiere."""

    return await create(payload)


async def checkout(payload: PresenzaCheckoutSchema) -> Presenza | None:
    """Chiude la presenza aperta più recente di un worker in un cantiere."""

    checkout_time: datetime = payload.checkout or datetime.now(timezone.utc)
    doc = await _collection().find_one_and_update(
        {
            "worker_id": payload.worker_id,
            "cantiere_id": payload.cantiere_id,
            "checkout": None,
        },
        {"$set": {"checkout": checkout_time}},
        sort=[("checkin", -1)],
        return_document=ReturnDocument.AFTER,
    )
    return Presenza(**doc) if doc else None
