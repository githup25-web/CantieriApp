from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from backend.core.database import get_collection
from backend.dependencies.phase6 import (
    TenantContext,
    require_admin,
    require_worker_or_admin,
)
from backend.models.presence import PresenceDB
from backend.schemas.presence import (
    PresenceCheckInSchema,
    PresenceCheckOutSchema,
    PresenceResponseSchema,
)

router = APIRouter(prefix="/presences", tags=["presences"])


def _presence_response(presence: PresenceDB) -> PresenceResponseSchema:
    return PresenceResponseSchema(
        id=presence.id,
        tenantId=presence.tenant_id,
        userId=presence.user_id,
        date=presence.attendance_date,
        checkIn=presence.check_in.isoformat() if presence.check_in else None,
        checkOut=presence.check_out.isoformat() if presence.check_out else None,
        notes=presence.notes,
    )


@router.post(
    "/check-in",
    response_model=PresenceResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def check_in(
    payload: PresenceCheckInSchema,
    context: TenantContext = Depends(require_worker_or_admin),
) -> PresenceResponseSchema:
    """Crea una sola presenza aperta per utente, tenant e giornata UTC."""

    now = datetime.now(timezone.utc)
    attendance_date = now.date().isoformat()
    presences_collection = get_collection("presences")
    query = {
        "tenantId": context.tenant_id,
        "userId": context.user.id,
        "date": attendance_date,
    }
    if await presences_collection.find_one(query) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Presence already exists for today",
        )

    presence = PresenceDB(
        tenantId=context.tenant_id,
        userId=context.user.id,
        date=attendance_date,
        checkIn=now,
        notes=payload.notes,
    )
    try:
        await presences_collection.insert_one(presence.model_dump(by_alias=True))
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Presence already exists for today",
        ) from exc
    return _presence_response(presence)


@router.post("/check-out", response_model=PresenceResponseSchema)
async def check_out(
    payload: PresenceCheckOutSchema,
    context: TenantContext = Depends(require_worker_or_admin),
) -> PresenceResponseSchema:
    """Chiude la presenza aperta dell'utente nel tenant e nella giornata correnti."""

    now = datetime.now(timezone.utc)
    query = {
        "tenantId": context.tenant_id,
        "userId": context.user.id,
        "date": now.date().isoformat(),
        "checkIn": {"$ne": None},
        "checkOut": None,
    }
    update_data: dict[str, object] = {"checkOut": now}
    if "notes" in payload.model_fields_set:
        update_data["notes"] = payload.notes

    updated_presence_doc = await get_collection("presences").find_one_and_update(
        query,
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    if updated_presence_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open presence found for today",
        )
    return _presence_response(PresenceDB(**updated_presence_doc))


@router.get("/me", response_model=list[PresenceResponseSchema])
async def list_my_presences(
    context: TenantContext = Depends(require_worker_or_admin),
) -> list[PresenceResponseSchema]:
    """Elenca esclusivamente le presenze dell'utente nel suo tenant."""

    presence_docs = await get_collection("presences").find(
        {"tenantId": context.tenant_id, "userId": context.user.id}
    ).sort([("date", -1), ("checkIn", -1)]).to_list(length=100)
    return [_presence_response(PresenceDB(**presence_doc)) for presence_doc in presence_docs]


@router.get("/", response_model=list[PresenceResponseSchema])
async def list_tenant_presences(
    context: TenantContext = Depends(require_admin),
) -> list[PresenceResponseSchema]:
    """Elenca tutte le presenze del tenant per admin e owner."""

    presence_docs = await get_collection("presences").find(
        {"tenantId": context.tenant_id}
    ).sort([("date", -1), ("checkIn", -1)]).to_list(length=100)
    return [_presence_response(PresenceDB(**presence_doc)) for presence_doc in presence_docs]
