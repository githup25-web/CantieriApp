"""Route Motor per i Task di cantiere (schema PASSO 1)."""

from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, status

from backend.schemas.task_schema import (
    TaskCreateSchema,
    TaskResponseSchema,
    TaskUpdateSchema,
)
from backend.services import task_service

router = APIRouter(prefix="/tasks", tags=["cantiere-tasks"])


@router.post(
    "/create",
    response_model=TaskResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(payload: TaskCreateSchema) -> TaskResponseSchema:
    """Crea un nuovo task per un cantiere."""

    task = await task_service.create(payload)
    return TaskResponseSchema(**task.model_dump())


@router.get("/by-cantiere/{cantiere_id}", response_model=list[TaskResponseSchema])
async def list_tasks_by_cantiere(cantiere_id: str) -> list[TaskResponseSchema]:
    """Elenca i task di un cantiere."""

    tasks = await task_service.get_by_cantiere(cantiere_id)
    return [TaskResponseSchema(**task.model_dump()) for task in tasks]


@router.patch("/update/{task_id}", response_model=TaskResponseSchema)
async def update_task(task_id: str, payload: TaskUpdateSchema) -> TaskResponseSchema:
    """Aggiorna parzialmente un task esistente."""

    try:
        task = await task_service.update(task_id, payload)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task id non valido",
        ) from exc

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task non trovato")
    return TaskResponseSchema(**task.model_dump())
