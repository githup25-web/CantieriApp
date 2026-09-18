from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from pydantic import BaseModel

from app.core.event_bus import emit_event
from app.core.security import get_current_user
from app.core.s3 import upload_pdf_to_minio
from app.models.cantiere import Cantiere
from app.models.fattura import Fattura
from app.models.membership import Membership
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/fattura", tags=["fattura"])


class FatturaCreateRequest(BaseModel):
    cantiere_id: UUID
    number: str | None = None  # se non fornito, generiamo
    description: str | None = None
    amount: float


class UploadPdfResponse(BaseModel):
    pdf_url: str | None = None


class FatturaResponse(BaseModel):
    id: str
    cantiere_id: str
    organization_id: str
    user_id: str
    number: str
    description: str | None = None
    amount: float
    status: str
    pdf_url: str | None = None
    created_at: str
    updated_at: str


class FatturaUpdateStatusRequest(BaseModel):
    status: str  # emessa, pagata, scaduta


def _allowed_status(status_value: str, allowed: set[str]) -> None:
    if status_value not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_value}")


async def _get_membership_org(current_user: User) -> UUID:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")
    return membership.organization_id


async def _ensure_fattura_belongs_to_user_org(current_user: User, fattura: Fattura) -> None:
    membership = await Membership.find_one(
        Membership.user_id == current_user.id,
        Membership.organization_id == fattura.organization_id,
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed for this organization")


async def _generate_invoice_number(organization_id: UUID) -> str:
    # Generazione semplice non atomica:
    # FAT-{YYYY}-{running3digits}, basata sull'ultima fattura creata.
    now = datetime.now(timezone.utc)
    year = now.year

    latest = await Fattura.find(
        Fattura.organization_id == organization_id,
        Fattura.created_at >= datetime(year, 1, 1, tzinfo=timezone.utc),
        Fattura.created_at < datetime(year + 1, 1, 1, tzinfo=timezone.utc),
    ).sort(-Fattura.created_at).limit(1).to_list()  # type: ignore[operator]

    if not latest:
        seq = 1
    else:
        # prova a estrarre sequenza da FAT-YYYY-XYZ
        last_num = latest[0].number
        try:
            seq = int(last_num.split("-")[-1]) + 1
        except Exception:
            seq = 1

    return f"FAT-{year}-{seq:03d}"


@router.post("/create", response_model=FatturaResponse, status_code=status.HTTP_201_CREATED)
async def create_fattura(
    payload: FatturaCreateRequest,
    current_user: User = Depends(get_current_user),
) -> FatturaResponse:
    organization_id = await _get_membership_org(current_user)

    cantiere = await Cantiere.get(payload.cantiere_id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    if cantiere.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Cantiere not in your organization")

    number = payload.number or await _generate_invoice_number(organization_id)

    fattura = Fattura(
        cantiere_id=payload.cantiere_id,
        organization_id=organization_id,
        user_id=current_user.id,
        number=number,
        description=payload.description,
        amount=payload.amount,
        status="emessa",
        pdf_url=None,
    )
    await fattura.insert()

    # Best-effort: don't block API response if event dispatch fails.
    try:
        await emit_event(
            event_name="fattura.created",
            payload={
                "organization_id": organization_id,
                "entity_id": fattura.id,
                "data": {"fattura_id": str(fattura.id), "number": fattura.number},
            },
        )
    except Exception:
        pass

    return FatturaResponse(
        id=str(fattura.id),
        cantiere_id=str(fattura.cantiere_id),
        organization_id=str(fattura.organization_id),
        user_id=str(fattura.user_id),
        number=fattura.number,
        description=fattura.description,
        amount=fattura.amount,
        status=fattura.status,
        pdf_url=fattura.pdf_url,
        created_at=fattura.created_at.isoformat(),
        updated_at=fattura.updated_at.isoformat(),
    )


@router.post("/{id}/upload-pdf", response_model=FatturaResponse)
async def upload_fattura_pdf(
    id: UUID = Path(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> FatturaResponse:
    fattura = await Fattura.get(id)
    if not fattura:
        raise HTTPException(status_code=404, detail="Fattura not found")

    await _ensure_fattura_belongs_to_user_org(current_user, fattura)

    object_name = f"fatture/{fattura.organization_id}/{fattura.cantiere_id}/{fattura.id}_{file.filename}"

    upload_result = await upload_pdf_to_minio(file=file, object_name=object_name)

    fattura.pdf_url = upload_result.pdf_url
    fattura.updated_at = datetime.now(timezone.utc)
    await fattura.save()

    try:
        await emit_event(
            event_name="fattura.pdf_uploaded",
            payload={
                "organization_id": fattura.organization_id,
                "entity_id": fattura.id,
                "data": {"pdf_url": fattura.pdf_url},
            },
        )
    except Exception:
        pass

    return FatturaResponse(
        id=str(fattura.id),
        cantiere_id=str(fattura.cantiere_id),
        organization_id=str(fattura.organization_id),
        user_id=str(fattura.user_id),
        number=fattura.number,
        description=fattura.description,
        amount=fattura.amount,
        status=fattura.status,
        pdf_url=fattura.pdf_url,
        created_at=fattura.created_at.isoformat(),
        updated_at=fattura.updated_at.isoformat(),
    )


@router.post("/{id}/update-status", response_model=FatturaResponse)
async def update_fattura_status(
    payload: FatturaUpdateStatusRequest,
    id: UUID = Path(...),
    current_user: User = Depends(check_role(["owner", "admin", "accountant"])),
) -> FatturaResponse:
    fattura = await Fattura.get(id)
    if not fattura:
        raise HTTPException(status_code=404, detail="Fattura not found")

    await _ensure_fattura_belongs_to_user_org(current_user, fattura)

    _allowed_status(payload.status, {"emessa", "pagata", "scaduta"})
    fattura.status = payload.status
    fattura.updated_at = datetime.now(timezone.utc)
    await fattura.save()

    try:
        await emit_event(
            event_name="fattura.status_changed",
            payload={
                "organization_id": fattura.organization_id,
                "entity_id": fattura.id,
                "data": {"status": fattura.status},
            },
        )
    except Exception:
        pass

    return FatturaResponse(
        id=str(fattura.id),
        cantiere_id=str(fattura.cantiere_id),
        organization_id=str(fattura.organization_id),
        user_id=str(fattura.user_id),
        number=fattura.number,
        description=fattura.description,
        amount=fattura.amount,
        status=fattura.status,
        pdf_url=fattura.pdf_url,
        created_at=fattura.created_at.isoformat(),
        updated_at=fattura.updated_at.isoformat(),
    )


@router.get("/cantiere/{id}", response_model=list[FatturaResponse])
async def list_fatture_by_cantiere(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[FatturaResponse]:
    cantiere = await Cantiere.get(id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere not found")

    membership = await Membership.find_one(
        Membership.user_id == current_user.id,
        Membership.organization_id == cantiere.organization_id,
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Not allowed for this organization")

    fatture = await Fattura.find(Fattura.cantiere_id == id).to_list()

    return [
        FatturaResponse(
            id=str(f.id),
            cantiere_id=str(f.cantiere_id),
            organization_id=str(f.organization_id),
            user_id=str(f.user_id),
            number=f.number,
            description=f.description,
            amount=f.amount,
            status=f.status,
            pdf_url=f.pdf_url,
            created_at=f.created_at.isoformat(),
            updated_at=f.updated_at.isoformat(),
        )
        for f in fatture
    ]


@router.get("/{id}", response_model=FatturaResponse)
async def get_fattura(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> FatturaResponse:
    fattura = await Fattura.get(id)
    if not fattura:
        raise HTTPException(status_code=404, detail="Fattura not found")

    await _ensure_fattura_belongs_to_user_org(current_user, fattura)

    return FatturaResponse(
        id=str(fattura.id),
        cantiere_id=str(fattura.cantiere_id),
        organization_id=str(fattura.organization_id),
        user_id=str(fattura.user_id),
        number=fattura.number,
        description=fattura.description,
        amount=fattura.amount,
        status=fattura.status,
        pdf_url=fattura.pdf_url,
        created_at=fattura.created_at.isoformat(),
        updated_at=fattura.updated_at.isoformat(),
    )
