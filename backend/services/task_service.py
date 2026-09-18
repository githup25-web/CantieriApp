"""Servizio Motor per la gestione dei Task di cantiere (schema PASSO 1)."""

from bson import ObjectId
from pymongo import ReturnDocument

from backend.core.database import get_collection
from backend.models.task import Task
from backend.schemas.task_schema import TaskCreateSchema, TaskUpdateSchema

COLLECTION_NAME = "cantiere_tasks"


def _collection():
    return get_collection(COLLECTION_NAME)


async def create(payload: TaskCreateSchema) -> Task:
    """Crea un nuovo task per un cantiere."""

    task = Task(**payload.model_dump())
    await _collection().insert_one(task.model_dump(by_alias=True))
    return task


async def get_by_cantiere(cantiere_id: str) -> list[Task]:
    """Elenca i task di un cantiere, dal più recente."""

    docs = (
        await _collection()
        .find({"cantiere_id": cantiere_id})
        .sort("data_creazione", -1)
        .to_list(length=500)
    )
    return [Task(**doc) for doc in docs]


async def update(task_id: str, payload: TaskUpdateSchema) -> Task | None:
    """Aggiorna parzialmente un task esistente. Restituisce None se non trovato."""

    object_id = ObjectId(task_id)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        doc = await _collection().find_one({"_id": object_id})
        return Task(**doc) if doc else None

    doc = await _collection().find_one_and_update(
        {"_id": object_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    return Task(**doc) if doc else None
