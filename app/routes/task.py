from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.membership import Membership
from app.models.task import Task
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(tags=["task"])


class TaskCreateRequest(BaseModel):
    cantiere_id: UUID
    organization_id: UUID
    title: str
    description: str
    assigned_to: UUID | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: UUID | None = None
    status: str | None = None
    progress: int | None = None


class TaskResponse(BaseModel):
    id: str | None = None
    cantiere_id: str
    organization_id: str
    title: str
    description: str
    assigned_to: str | None = None
    status: str
    progress: int
    created_at: str
    updated_at: str


class ProgressSummaryResponse(BaseModel):
    percentage: int
    completed_tasks: int
    total_tasks: int


@router.post("/task/create", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateRequest, current_user: User = Depends(get_current_user)) -> TaskResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    task = Task(
        cantiere_id=payload.cantiere_id,
        organization_id=payload.organization_id,
        title=payload.title,
        description=payload.description,
        assigned_to=payload.assigned_to,
        status="todo",
        progress=0,
    )
    await task.insert()

    return TaskResponse(
        id=str(task.id),
        cantiere_id=str(task.cantiere_id),
        organization_id=str(task.organization_id),
        title=task.title,
        description=task.description,
        assigned_to=str(task.assigned_to) if task.assigned_to else None,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.post("/task/update/{id}", response_model=TaskResponse)
async def update_task(
    id: UUID = Path(...),
    payload: TaskUpdateRequest = None,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    if payload is None:
        payload = TaskUpdateRequest()
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.assigned_to is not None:
        task.assigned_to = payload.assigned_to
    if payload.status is not None:
        task.status = payload.status
    if payload.progress is not None:
        task.progress = payload.progress

    task.updated_at = datetime.now(timezone.utc)
    await task.save()

    return TaskResponse(
        id=str(task.id),
        cantiere_id=str(task.cantiere_id),
        organization_id=str(task.organization_id),
        title=task.title,
        description=task.description,
        assigned_to=str(task.assigned_to) if task.assigned_to else None,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.get("/task/cantiere/{id}", response_model=list[TaskResponse])
async def get_tasks_by_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    tasks = await Task.find(Task.cantiere_id == id).to_list()
    return [
        TaskResponse(
            id=str(t.id),
            cantiere_id=str(t.cantiere_id),
            organization_id=str(t.organization_id),
            title=t.title,
            description=t.description,
            assigned_to=str(t.assigned_to) if t.assigned_to else None,
            status=t.status,
            progress=t.progress,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
        )
        for t in tasks
    ]


@router.get("/task/{id}", response_model=TaskResponse)
async def get_task(id: UUID = Path(...), current_user: User = Depends(get_current_user)) -> TaskResponse:
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        id=str(task.id),
        cantiere_id=str(task.cantiere_id),
        organization_id=str(task.organization_id),
        title=task.title,
        description=task.description,
        assigned_to=str(task.assigned_to) if task.assigned_to else None,
        status=task.status,
        progress=task.progress,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )


@router.delete("/task/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> None:
    task = await Task.get(id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await task.delete()


@router.get("/cantiere/{id}/progress", response_model=ProgressSummaryResponse)
async def get_cantiere_progress(id: UUID = Path(...), current_user: User = Depends(get_current_user)) -> ProgressSummaryResponse:
    tasks = await Task.find(Task.cantiere_id == id).to_list()
    total_tasks = len(tasks)
    completed_tasks = sum(1 for task in tasks if task.status == "done")
    percentage = 0 if total_tasks == 0 else int(sum(task.progress for task in tasks) / total_tasks)

    return ProgressSummaryResponse(
        percentage=percentage,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
    )
