from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.core.event_bus import emit_event
from app.core.security import get_current_user
from app.models.membership import Membership
from app.models.presence import Presence
from app.models.user import User
from app.routes.organization import check_role

router = APIRouter(prefix="/presence", tags=["presence"])


class PresencePayload(BaseModel):
    cantiere_id: UUID
    gps_lat: float
    gps_lon: float
    note: str | None = None
    weather: str | None = None


class PresenceResponse(BaseModel):
    id: str | None = None
    user_id: str
    organization_id: str
    cantiere_id: str
    type: str
    gps_lat: float
    gps_lon: float
    timestamp: str
    note: str | None = None
    weather: str | None = None


@router.post("/clock-in", response_model=PresenceResponse, status_code=status.HTTP_201_CREATED)
async def clock_in(payload: PresencePayload, current_user: User = Depends(get_current_user)) -> PresenceResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    presence = Presence(
        user_id=current_user.id,
        organization_id=membership.organization_id,
        cantiere_id=payload.cantiere_id,
        type="entrata",
        gps_lat=payload.gps_lat,
        gps_lon=payload.gps_lon,
        note=payload.note,
        weather=payload.weather,
    )
    await presence.insert()

    try:
        await emit_event(
            event_name="presenza.created",
            payload={
                "organization_id": presence.organization_id,
                "entity_id": presence.id,
                "data": {"presence_id": str(presence.id), "cantiere_id": str(presence.cantiere_id), "type": presence.type},
            },
        )
    except Exception:
        pass

    return PresenceResponse(
        id=str(presence.id),
        user_id=str(presence.user_id),
        organization_id=str(presence.organization_id),
        cantiere_id=str(presence.cantiere_id),
        type=presence.type,
        gps_lat=presence.gps_lat,
        gps_lon=presence.gps_lon,
        timestamp=presence.timestamp.isoformat(),
        note=presence.note,
        weather=presence.weather,
    )


@router.post("/clock-out", response_model=PresenceResponse, status_code=status.HTTP_201_CREATED)
async def clock_out(payload: PresencePayload, current_user: User = Depends(get_current_user)) -> PresenceResponse:
    membership = await Membership.find_one(Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="User is not a member of any organization")

    presence = Presence(
        user_id=current_user.id,
        organization_id=membership.organization_id,
        cantiere_id=payload.cantiere_id,
        type="uscita",
        gps_lat=payload.gps_lat,
        gps_lon=payload.gps_lon,
        note=payload.note,
        weather=payload.weather,
    )
    await presence.insert()

    try:
        await emit_event(
            event_name="presenza.created",
            payload={
                "organization_id": presence.organization_id,
                "entity_id": presence.id,
                "data": {"presence_id": str(presence.id), "cantiere_id": str(presence.cantiere_id), "type": presence.type},
            },
        )
    except Exception:
        pass

    return PresenceResponse(
        id=str(presence.id),
        user_id=str(presence.user_id),
        organization_id=str(presence.organization_id),
        cantiere_id=str(presence.cantiere_id),
        type=presence.type,
        gps_lat=presence.gps_lat,
        gps_lon=presence.gps_lon,
        timestamp=presence.timestamp.isoformat(),
        note=presence.note,
        weather=presence.weather,
    )


@router.get("/my", response_model=list[PresenceResponse])
async def get_my_presences(current_user: User = Depends(get_current_user)) -> list[PresenceResponse]:
    presences = await Presence.find(Presence.user_id == current_user.id).to_list()
    return [
        PresenceResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            organization_id=str(p.organization_id),
            cantiere_id=str(p.cantiere_id),
            type=p.type,
            gps_lat=p.gps_lat,
            gps_lon=p.gps_lon,
            timestamp=p.timestamp.isoformat(),
            note=p.note,
            weather=p.weather,
        )
        for p in presences
    ]


@router.get("/cantiere/{id}", response_model=list[PresenceResponse])
async def get_cantiere_presences(
    id: UUID = Path(...),
    current_user: User = Depends(check_role("manager")),
) -> list[PresenceResponse]:
    presences = await Presence.find(Presence.cantiere_id == id).to_list()
    return [
        PresenceResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            organization_id=str(p.organization_id),
            cantiere_id=str(p.cantiere_id),
            type=p.type,
            gps_lat=p.gps_lat,
            gps_lon=p.gps_lon,
            timestamp=p.timestamp.isoformat(),
            note=p.note,
            weather=p.weather,
        )
        for p in presences
    ]
