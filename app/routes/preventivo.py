from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.s3 import upload_pdf_to_minio
from app.models.cantiere import Cantiere
from app.models.membership import Membership
from app.models.preventivo import Preventivo
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/preventivo", tags=["preventivo"])


class PreventivoCreateRequest(BaseModel):
    cantiere_id: UUID
    title: str
    description: str | None = None
    amount: float


class PreventivoResponse(BaseModel):
    id: str
    cantiere_id: str
    organization_id: str
    user_id: str
    title: str
    description: str | None = None
    amount: float
    status: str
    pdf_url: str | None = None
    version: int
    created_at: str
    updated_at: str


class PreventivoUpdateStatusRequest(BaseModel):
    status: str  # bozza, inviato, approvato, rifiutato


def _allowed_status(status_value: str, allowed: set[str]) -> None:
    if status_value not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_value}")


async def _get_membership_org(current_user: User) -> UUID:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")
    return membership.organization_id


async def _ensure_preventivo_belongs_to_user_org(current_user: User, preventivo: Preventivo) -> None:
    membership = await Membership.find_one(
        Membership.user_id == current_user.id,
        Membership.organization_id == preventivo.organization_id,
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed for this organization")


@router.post("/create", response_model=PreventivoResponse, status_code=status.HTTP_201_CREATED)
async def create_preventivo(
    payload: PreventivoCreateRequest,
    current_user: User = Depends(get_current_user),
) -> PreventivoResponse:
    organization_id = await _get_membership_org(current_user)

    cantiere = await Cantiere.get(payload.cantiere_id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    if cantiere.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Cantiere not in your organization")

    preventivo = Preventivo(
        cantiere_id=payload.cantiere_id,
        organization_id=organization_id,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        amount=payload.amount,
        status="bozza",
        pdf_url=None,
        version=1,
    )
    await preventivo.insert()

    return PreventivoResponse(
        id=str(preventivo.id),
        cantiere_id=str(preventivo.cantiere_id),
        organization_id=str(preventivo.organization_id),
        user_id=str(preventivo.user_id),
        title=preventivo.title,
        description=preventivo.description,
        amount=preventivo.amount,
        status=preventivo.status,
        pdf_url=preventivo.pdf_url,
        version=preventivo.version,
        created_at=preventivo.created_at.isoformat(),
        updated_at=preventivo.updated_at.isoformat(),
    )


@router.post("/{id}/upload-pdf", response_model=PreventivoResponse)
async def upload_preventivo_pdf(
    id: UUID = Path(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> PreventivoResponse:
    preventivo = await Preventivo.get(id)
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo not found")

    await _ensure_preventivo_belongs_to_user_org(current_user, preventivo)

    object_name = f"preventivi/{preventivo.organization_id}/{preventivo.cantiere_id}/{preventivo.id}/v{preventivo.version + 1}_{file.filename}"

    upload_result = await upload_pdf_to_minio(file=file, object_name=object_name)

    preventivo.version = (preventivo.version or 1) + 1
    preventivo.pdf_url = upload_result.pdf_url
    preventivo.updated_at = datetime.now(timezone.utc)

    await preventivo.save()

    return PreventivoResponse(
        id=str(preventivo.id),
        cantiere_id=str(preventivo.cantiere_id),
        organization_id=str(preventivo.organization_id),
        user_id=str(preventivo.user_id),
        title=preventivo.title,
        description=preventivo.description,
        amount=preventivo.amount,
        status=preventivo.status,
        pdf_url=preventivo.pdf_url,
        version=preventivo.version,
        created_at=preventivo.created_at.isoformat(),
        updated_at=preventivo.updated_at.isoformat(),
    )


@router.post("/{id}/update-status", response_model=PreventivoResponse)
async def update_preventivo_status(
    payload: PreventivoUpdateStatusRequest,
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "manager"])),
) -> PreventivoResponse:
    preventivo = await Preventivo.get(id)
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo not found")

    await _ensure_preventivo_belongs_to_user_org(current_user, preventivo)

    _allowed_status(payload.status, {"bozza", "inviato", "approvato", "rifiutato"})
    preventivo.status = payload.status
    preventivo.updated_at = datetime.now(timezone.utc)

    await preventivo.save()

    return PreventivoResponse(
        id=str(preventivo.id),
        cantiere_id=str(preventivo.cantiere_id),
        organization_id=str(preventivo.organization_id),
        user_id=str(preventivo.user_id),
        title=preventivo.title,
        description=preventivo.description,
        amount=preventivo.amount,
        status=preventivo.status,
        pdf_url=preventivo.pdf_url,
        version=preventivo.version,
        created_at=preventivo.created_at.isoformat(),
        updated_at=preventivo.updated_at.isoformat(),
    )


@router.get("/cantiere/{id}", response_model=list[PreventivoResponse])
async def list_preventivi_by_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[PreventivoResponse]:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    # membership check on organization_id
    membership = await Membership.find_one(
        Membership.user_id == current_user.id,
        Membership.organization_id == cantiere.organization_id,
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed for this organization")

    preventivi = await Preventivo.find(Preventivo.cantiere_id == id).to_list()

    return [
        PreventivoResponse(
            id=str(p.id),
            cantiere_id=str(p.cantiere_id),
            organization_id=str(p.organization_id),
            user_id=str(p.user_id),
            title=p.title,
            description=p.description,
            amount=p.amount,
            status=p.status,
            pdf_url=p.pdf_url,
            version=p.version,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in preventivi
    ]


@router.get("/{id}", response_model=PreventivoResponse)
async def get_preventivo(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> PreventivoResponse:
    preventivo = await Preventivo.get(id)
    if not preventivo:
        raise HTTPException(status_code=404, detail="Preventivo not found")

    await _ensure_preventivo_belongs_to_user_org(current_user, preventivo)

    return PreventivoResponse(
        id=str(preventivo.id),
        cantiere_id=str(preventivo.cantiere_id),
        organization_id=str(preventivo.organization_id),
        user_id=str(preventivo.user_id),
        title=preventivo.title,
        description=preventivo.description,
        amount=preventivo.amount,
        status=preventivo.status,
        pdf_url=preventivo.pdf_url,
        version=preventivo.version,
        created_at=preventivo.created_at.isoformat(),
        updated_at=preventivo.updated_at.isoformat(),
    )
