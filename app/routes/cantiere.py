from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.cantiere import Cantiere
from app.models.membership import Membership
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/cantiere", tags=["cantiere"])


class CantiereCreateRequest(BaseModel):
    organization_id: UUID
    title: str
    description: str | None = None


class AssignWorkerRequest(BaseModel):
    assigned_worker_id: UUID | None = None


class UpdateStatusRequest(BaseModel):
    status: str


class CantiereResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    description: str | None = None
    assigned_worker_id: str | None = None
    status: str
    created_at: str
    updated_at: str




async def _get_membership_or_403(current_user: User, organization_id: UUID) -> Membership:
    membership = await Membership.find_one(
        Membership.user_id == current_user.id,
        Membership.organization_id == organization_id,
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    return membership


@router.post("/create", response_model=CantiereResponse, status_code=status.HTTP_201_CREATED)
async def create_cantiere(payload: CantiereCreateRequest, current_user: User = Depends(get_current_user)) -> CantiereResponse:
    await _get_membership_or_403(current_user, payload.organization_id)

    cantiere = Cantiere(
        organization_id=payload.organization_id,
        title=payload.title,
        description=payload.description,
        assigned_worker_id=None,
        status="planned",
    )
    await cantiere.insert()

    return CantiereResponse(
        id=str(cantiere.id),
        organization_id=str(cantiere.organization_id),
        title=cantiere.title,
        description=cantiere.description,
        assigned_worker_id=str(cantiere.assigned_worker_id) if cantiere.assigned_worker_id else None,
        status=cantiere.status,
        created_at=cantiere.created_at.isoformat(),
        updated_at=cantiere.updated_at.isoformat(),
    )


@router.post("/{id}/assign-worker", response_model=CantiereResponse)
async def assign_worker(
    payload: AssignWorkerRequest,
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> CantiereResponse:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    # tenant check: ensure current_user belongs to the cantiere organization
    await _get_membership_or_403(current_user, cantiere.organization_id)

    cantiere.assigned_worker_id = payload.assigned_worker_id
    cantiere.updated_at = datetime.now(timezone.utc)
    await cantiere.save()

    return CantiereResponse(
        id=str(cantiere.id),
        organization_id=str(cantiere.organization_id),
        title=cantiere.title,
        description=cantiere.description,
        assigned_worker_id=str(cantiere.assigned_worker_id) if cantiere.assigned_worker_id else None,
        status=cantiere.status,
        created_at=cantiere.created_at.isoformat(),
        updated_at=cantiere.updated_at.isoformat(),
    )


@router.post("/{id}/update-status", response_model=CantiereResponse)
async def update_status(
    payload: UpdateStatusRequest,
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> CantiereResponse:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    await _get_membership_or_403(current_user, cantiere.organization_id)

    cantiere.status = payload.status
    cantiere.updated_at = datetime.now(timezone.utc)
    await cantiere.save()

    return CantiereResponse(
        id=str(cantiere.id),
        organization_id=str(cantiere.organization_id),
        title=cantiere.title,
        description=cantiere.description,
        assigned_worker_id=str(cantiere.assigned_worker_id) if cantiere.assigned_worker_id else None,
        status=cantiere.status,
        created_at=cantiere.created_at.isoformat(),
        updated_at=cantiere.updated_at.isoformat(),
    )


@router.get("/my", response_model=list[CantiereResponse])
async def get_my_cantieri(current_user: User = Depends(get_current_user)) -> list[CantiereResponse]:
    memberships = await Membership.find(Membership.user_id == current_user.id).to_list()
    organization_ids = [m.organization_id for m in memberships]

    # type: ignore[attr-defined]
    cantieri = await Cantiere.find(Cantiere.organization_id.in_(organization_ids)).to_list()

    return [
        CantiereResponse(
            id=str(c.id),
            organization_id=str(c.organization_id),
            title=c.title,
            description=c.description,
            assigned_worker_id=str(c.assigned_worker_id) if c.assigned_worker_id else None,
            status=c.status,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in cantieri
    ]


@router.get("/{id}", response_model=CantiereResponse)
async def get_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> CantiereResponse:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    await _get_membership_or_403(current_user, cantiere.organization_id)

    return CantiereResponse(
        id=str(cantiere.id),
        organization_id=str(cantiere.organization_id),
        title=cantiere.title,
        description=cantiere.description,
        assigned_worker_id=str(cantiere.assigned_worker_id) if cantiere.assigned_worker_id else None,
        status=cantiere.status,
        created_at=cantiere.created_at.isoformat(),
        updated_at=cantiere.updated_at.isoformat(),
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> None:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    await _get_membership_or_403(current_user, cantiere.organization_id)

    await cantiere.delete()
