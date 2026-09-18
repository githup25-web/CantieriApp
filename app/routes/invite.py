from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

from app.core.security import get_current_user, get_password_hash
from app.models.invite import Invite
from app.models.membership import Membership
from app.models.user import User

router = APIRouter(prefix="/invite", tags=["invite"])


class CreateInviteRequest(BaseModel):
    email: EmailStr
    role: str
    organization_id: UUID


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str


class InviteResponse(BaseModel):
    id: str | None = None
    email: str
    role: str
    organization_id: str
    token: str
    status: str
    expires_at: datetime


@router.post("/create", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(payload: CreateInviteRequest, current_user: User = Depends(get_current_user)) -> InviteResponse:
    invite = Invite(
        email=str(payload.email),
        role=payload.role,
        organization_id=payload.organization_id,
        status="pending",
    )
    await invite.insert()

    invite_link = f"https://app.cantiereapp.com/invite?token={invite.token}"

    return InviteResponse(
        id=str(invite.id),
        email=str(invite.email),
        role=invite.role,
        organization_id=str(invite.organization_id),
        token=invite.token,
        status=invite.status,
        expires_at=invite.expires_at,
    )


@router.get("/verify", response_model=InviteResponse)
async def verify_invite(token: str = Query(...)) -> InviteResponse:
    invite = await Invite.find_one(Invite.token == token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.status == "accepted":
        raise HTTPException(status_code=400, detail="Invite already accepted")

    if invite.is_expired():
        invite.status = "expired"
        await invite.save()
        raise HTTPException(status_code=410, detail="Invite expired")

    return InviteResponse(
        id=str(invite.id),
        email=str(invite.email),
        role=invite.role,
        organization_id=str(invite.organization_id),
        token=invite.token,
        status=invite.status,
        expires_at=invite.expires_at,
    )


@router.post("/accept", response_model=dict)
async def accept_invite(payload: AcceptInviteRequest) -> dict:
    invite = await Invite.find_one(Invite.token == payload.token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.status == "accepted":
        raise HTTPException(status_code=400, detail="Invite already accepted")

    if invite.is_expired():
        invite.status = "expired"
        await invite.save()
        raise HTTPException(status_code=410, detail="Invite expired")

    existing_user = await User.find_one(User.email == str(invite.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        email=str(invite.email),
        full_name=payload.name,
        hashed_password=get_password_hash(payload.password),
        organization_id=str(invite.organization_id),
    )
    await user.insert()

    membership = Membership(
        user_id=user.id,
        organization_id=invite.organization_id,
        role=invite.role,
    )
    await membership.insert()

    invite.status = "accepted"
    await invite.save()

    return {"message": "Invite accepted", "email": str(invite.email)}
