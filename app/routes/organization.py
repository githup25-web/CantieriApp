from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.membership import Membership
from app.models.organization import Organization, OrganizationCreate, OrganizationPublic
from app.models.user import User

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationCreateRequest(OrganizationCreate):
    pass


class OrganizationResponse(OrganizationPublic):
    pass


class MemberResponse(BaseModel):
    user_id: UUID
    organization_id: UUID
    role: str
    user_email: str | None = None


class RoleCheck:
    def __init__(self, required_roles: str | list[str]):
        self.required_roles = [required_roles] if isinstance(required_roles, str) else required_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_id = current_user.id
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user")

        membership = await Membership.find_one(
            Membership.user_id == user_id,
        )
        if not membership or membership.role not in self.required_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user


def check_role(required_roles: str | list[str]):
    return RoleCheck(required_roles)


@router.post("/create", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreateRequest,
    current_user: User = Depends(get_current_user),
) -> OrganizationResponse:
    organization = Organization(name=payload.name, slug=payload.slug, description=payload.description)
    await organization.insert()

    membership = Membership(
        user_id=current_user.id,
        organization_id=organization.id,
        role="owner",
    )
    await membership.insert()

    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        description=organization.description,
        is_active=organization.is_active,
    )


@router.get("/my", response_model=list[OrganizationResponse])
async def get_my_organizations(current_user: User = Depends(get_current_user)) -> list[OrganizationResponse]:
    memberships = await Membership.find(Membership.user_id == current_user.id).to_list()
    organization_ids = [m.organization_id for m in memberships]

    organizations = await Organization.find(Organization.id.in_(organization_ids)).to_list()

    return [
        OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            is_active=org.is_active,
        )
        for org in organizations
    ]


@router.get("/{id}/members", response_model=list[MemberResponse])
async def get_organization_members(
    id: UUID = Path(...),
    current_user: User = Depends(get_current_user),
) -> list[MemberResponse]:
    membership = await Membership.find_one(Membership.organization_id == id, Membership.user_id == current_user.id)
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    memberships = await Membership.find(Membership.organization_id == id).to_list()

    users = await User.find(User.id.in_([m.user_id for m in memberships])).to_list()
    user_map = {str(u.id): u for u in users}

    return [
        MemberResponse(
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
            user_email=user_map.get(str(m.user_id)).email if str(m.user_id) in user_map else None,
        )
        for m in memberships
    ]
