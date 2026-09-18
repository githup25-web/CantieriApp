from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.database import get_collection
from backend.dependencies.phase6 import TenantContext, require_worker_or_admin
from backend.models.progress_photo import ProgressPhotoDB
from backend.schemas.progress_photo import (
    ProgressPhotoCreateSchema,
    ProgressPhotoResponseSchema,
)

router = APIRouter(prefix="/photos", tags=["photos"])


def _photo_response(photo: ProgressPhotoDB) -> ProgressPhotoResponseSchema:
    return ProgressPhotoResponseSchema(
        id=photo.id,
        tenantId=photo.tenant_id,
        taskId=photo.task_id,
        userId=photo.user_id,
        url=photo.url,
        createdAt=photo.created_at.isoformat(),
    )


async def _get_scoped_task(
    task_id: UUID,
    context: TenantContext,
) -> dict:
    query: dict[str, UUID] = {"_id": task_id, "tenantId": context.tenant_id}
    if not context.is_admin:
        query["assignedTo"] = context.user.id

    task_doc = await get_collection("tasks").find_one(query)
    if task_doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task_doc


@router.post(
    "/",
    response_model=ProgressPhotoResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_progress_photo(
    payload: ProgressPhotoCreateSchema,
    context: TenantContext = Depends(require_worker_or_admin),
) -> ProgressPhotoResponseSchema:
    """Associa una foto al task del tenant; il worker deve esserne assegnatario."""

    await _get_scoped_task(payload.task_id, context)
    photo = ProgressPhotoDB(
        tenantId=context.tenant_id,
        taskId=payload.task_id,
        userId=context.user.id,
        url=payload.url,
    )
    await get_collection("progress_photos").insert_one(photo.model_dump(by_alias=True))
    return _photo_response(photo)


@router.get("/task/{task_id}", response_model=list[ProgressPhotoResponseSchema])
async def list_task_photos(
    task_id: UUID,
    context: TenantContext = Depends(require_worker_or_admin),
) -> list[ProgressPhotoResponseSchema]:
    """Elenca le foto di un task visibile nel tenant corrente."""

    await _get_scoped_task(task_id, context)
    photo_docs = await get_collection("progress_photos").find(
        {"tenantId": context.tenant_id, "taskId": task_id}
    ).sort("createdAt", -1).to_list(length=100)
    return [_photo_response(ProgressPhotoDB(**photo_doc)) for photo_doc in photo_docs]


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_progress_photo(
    photo_id: UUID,
    context: TenantContext = Depends(require_worker_or_admin),
) -> None:
    """Elimina una foto del tenant; i worker possono eliminare solo le proprie."""

    query: dict[str, UUID] = {"_id": photo_id, "tenantId": context.tenant_id}
    if not context.is_admin:
        query["userId"] = context.user.id

    delete_result = await get_collection("progress_photos").delete_one(query)
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Progress photo not found",
        )