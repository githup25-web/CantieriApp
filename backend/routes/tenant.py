from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from backend.core.database import get_collection
from backend.dependencies.auth import get_current_user
from backend.models.tenant import (
    MembershipDB,
    MembershipResponse,
    TenantCreate,
    TenantDB,
    TenantPublic,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantPublic, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    current_user: dict = Depends(get_current_user),
) -> TenantPublic:
    """Create a new tenant/organization."""
    tenants_collection = get_collection("tenants")
    memberships_collection = get_collection("memberships")

    # Check if slug already exists
    existing = await tenants_collection.find_one({"slug": payload.slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant slug already exists",
        )

    # Create tenant document
    tenant = TenantDB(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
    )
    await tenants_collection.insert_one(tenant.model_dump(by_alias=True))

    # Create owner membership
    membership = MembershipDB(
        user_id=current_user["_id"],
        tenant_id=tenant.id,
        role="owner",
    )
    await memberships_collection.insert_one(membership.model_dump(by_alias=True))

    return TenantPublic(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        description=tenant.description,
        is_active=tenant.is_active,
    )


@router.get("/my", response_model=list[TenantPublic])
async def get_my_tenants(
    current_user: dict = Depends(get_current_user),
) -> list[TenantPublic]:
    """Get all tenants for the current user."""
    memberships_collection = get_collection("memberships")
    tenants_collection = get_collection("tenants")

    # Find all memberships for this user
    memberships = await memberships_collection.find(
        {"user_id": current_user["_id"]}
    ).to_list(length=100)

    if not memberships:
        return []

    # Get tenant IDs
    tenant_ids = [m["tenant_id"] for m in memberships]

    # Find all tenants
    tenants = await tenants_collection.find(
        {"_id": {"$in": tenant_ids}}
    ).to_list(length=100)

    return [
        TenantPublic(
            id=str(t["_id"]),
            name=t["name"],
            slug=t["slug"],
            description=t.get("description"),
            is_active=t.get("is_active", True),
        )
        for t in tenants
    ]


@router.get("/{id}/members", response_model=list[MembershipResponse])
async def get_tenant_members(
    id: UUID = Path(...),
    current_user: dict = Depends(get_current_user),
) -> list[MembershipResponse]:
    """Get all members of a tenant."""
    memberships_collection = get_collection("memberships")
    users_collection = get_collection("users")

    # Check if user is a member
    membership = await memberships_collection.find_one(
        {"tenant_id": id, "user_id": current_user["_id"]}
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this tenant",
        )

    # Get all memberships for this tenant
    memberships = await memberships_collection.find(
        {"tenant_id": id}
    ).to_list(length=100)

    # Get user details
    user_ids = [m["user_id"] for m in memberships]
    users = await users_collection.find(
        {"_id": {"$in": user_ids}}
    ).to_list(length=100)
    user_map = {str(u["_id"]): u for u in users}

    return [
        MembershipResponse(
            user_id=str(m["user_id"]),
            tenant_id=str(m["tenant_id"]),
            role=m["role"],
            user_email=user_map.get(str(m["user_id"]), {}).get("email"),
        )
        for m in memberships
    ]
