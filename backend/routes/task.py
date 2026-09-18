from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.database import get_collection
from backend.dependencies.phase6 import (
    TenantContext,
    require_admin,
    require_worker_or_admin,
)
from backend.models.task import TaskDB
from backend.schemas.task import (
    TaskCreateSchema,
    TaskResponseSchema,
    TaskUpdateSchema,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_response(task: TaskDB) -> TaskResponseSchema:
    return TaskResponseSchema(
        id=task.id,
        tenantId=task.tenant_id,
        title=task.title,
        description=task.description,
        assignedTo=task.assigned_to,
        status=task.status,
        createdAt=task.created_at.isoformat(),
        updatedAt=task.updated_at.isoformat(),
    )


async def _ensure_assignee_belongs_to_tenant(
    assigned_to: UUID,
    tenant_id: UUID,
) -> None:
    memberships_collection = get_collection("memberships")
    membership = await memberships_collection.find_one(
        {"userId": assigned_to, "tenantId": tenant_id}
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Assigned user is not a member of the active tenant",
        )


@router.post("/", response_model=TaskResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateSchema,
    context: TenantContext = Depends(require_admin),
) -> TaskResponseSchema:
    """Crea un task nel tenant dell'admin autenticato."""

    if payload.assigned_to is not None:
        await _ensure_assignee_belongs_to_tenant(payload.assigned_to, context.tenant_id)

    task = TaskDB(
        tenantId=context.tenant_id,
        title=payload.title,
        description=payload.description,
        assignedTo=payload.assigned_to,
    )
    await get_collection("tasks").insert_one(task.model_dump(by_alias=True))
    return _task_response(task)


@router.get("/", response_model=list[TaskResponseSchema])
async def list_tasks(
    context: TenantContext = Depends(require_worker_or_admin),
) -> list[TaskResponseSchema]:
    """Elenca tutti i task dell'admin o solo quelli assegnati al worker."""

    query: dict[str, UUID] = {"tenantId": context.tenant_id}
    if not context.is_admin:
        query["assignedTo"] = context.user.id

    task_docs = await get_collection("tasks").find(query).sort(
        "createdAt", -1
    ).to_list(length=100)
    return [_task_response(TaskDB(**task_doc)) for task_doc in task_docs]


@router.get("/{task_id}", response_model=TaskResponseSchema)
async def get_task(
    task_id: UUID,
    context: TenantContext = Depends(require_worker_or_admin),
) -> TaskResponseSchema:
    """Restituisce un task nel tenant corrente e, per worker, solo se assegnato."""

    query: dict[str, UUID] = {"_id": task_id, "tenantId": context.tenant_id}
    if not context.is_admin:
        query["assignedTo"] = context.user.id

    task_doc = await get_collection("tasks").find_one(query)
    if task_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _task_response(TaskDB(**task_doc))


@router.patch("/{task_id}", response_model=TaskResponseSchema)
async def update_task(
    task_id: UUID,
    payload: TaskUpdateSchema,
    context: TenantContext = Depends(require_admin),
) -> TaskResponseSchema:
    """Aggiorna un task senza uscire dal tenant dell'admin autenticato."""

    tasks_collection = get_collection("tasks")
    query = {"_id": task_id, "tenantId": context.tenant_id}
    if await tasks_collection.find_one(query) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = payload.model_dump(by_alias=True, exclude_unset=True)
    assigned_to = update_data.get("assignedTo")
    if assigned_to is not None:
        await _ensure_assignee_belongs_to_tenant(assigned_to, context.tenant_id)

    if update_data:
        update_data["updatedAt"] = datetime.now(timezone.utc)
        await tasks_collection.update_one(query, {"$set": update_data})

    updated_task_doc = await tasks_collection.find_one(query)
    if updated_task_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return _task_response(TaskDB(**updated_task_doc))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    context: TenantContext = Depends(require_admin),
) -> None:
    """Elimina un task esclusivamente dal tenant dell'admin autenticato."""

    delete_result = await get_collection("tasks").delete_one(
        {"_id": task_id, "tenantId": context.tenant_id}
    )
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
