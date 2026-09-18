from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError

from backend.core.database import get_collection
from backend.core.jwt import create_access_token, create_refresh_token, verify_token
from backend.core.security import get_password_hash, verify_password
from backend.dependencies.auth import get_current_user
from backend.models.tenant import MembershipDB, TenantDB
from backend.models.user import TokenResponse, UserCreate, UserDB, UserInDB, UserLogin, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: UserCreate) -> dict:
    """Register a new user with automatic tenant and membership creation.

    Creates a user document with hashed password, generates a tenant
    from the user's full name, creates a membership linking the user
    to the tenant with role 'admin', and returns JWT tokens along
    with user and tenant data.
    """
    users_collection = get_collection("users")
    tenants_collection = get_collection("tenants")
    memberships_collection = get_collection("memberships")

    # --- Check if email already exists ---
    existing = await users_collection.find_one({"email": payload.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # --- Create tenant from user's full name ---
    tenant_id = uuid4()
    base_slug = payload.full_name.lower().replace(" ", "-") if payload.full_name else "organization"
    slug = f"{base_slug}-{uuid4().hex[:6]}"
    tenant = TenantDB.model_construct(
        _id=tenant_id,
        name=f"{payload.full_name}'s Organization" if payload.full_name else "My Organization",
        slug=slug,
    )

    # --- Create user document with tenant_id ---
    user_id = uuid4()
    user = UserDB.model_construct(
        _id=user_id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        tenant_id=str(tenant_id),
    )

    # --- Create membership (admin role) ---
    membership = MembershipDB.model_construct(
        _id=uuid4(),
        userId=user_id,
        tenantId=tenant_id,
        role="admin",
    )

    # --- Persist to MongoDB ---
    await users_collection.insert_one(user.model_dump(by_alias=True))
    await tenants_collection.insert_one(tenant.model_dump(by_alias=True))
    await memberships_collection.insert_one(membership.model_dump(by_alias=True))

    # --- Generate JWT tokens with tenantId and role ---
    access_token = create_access_token(
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        role="admin",
    )
    refresh_token = create_refresh_token(user_id=str(user_id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user_id),
            "email": payload.email,
            "full_name": payload.full_name,
            "tenant_id": str(tenant_id),
        },
        "tenant": {
            "id": str(tenant_id),
            "name": tenant.name,
            "slug": tenant.slug,
            "is_active": True,
        },
    }


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin) -> TokenResponse:
    """Authenticate a user and return JWT tokens with tenant context.

    Verifies email and password, looks up the user's membership to
    extract tenantId and role, then generates access and refresh tokens.
    """
    users_collection = get_collection("users")
    memberships_collection = get_collection("memberships")

    # --- Find user by email ---
    user_doc = await users_collection.find_one({"email": payload.email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # --- Verify password ---
    if not verify_password(payload.password, user_doc["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # --- Check if user is active ---
    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # --- Find membership to get tenantId and role ---
    user_id = user_doc["_id"]
    membership_doc = await memberships_collection.find_one({"userId": user_id})
    if not membership_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no tenant membership",
        )

    tenant_id = str(membership_doc["tenantId"])
    role = membership_doc.get("role", "worker")

    # --- Generate JWT tokens ---
    access_token = create_access_token(
        user_id=str(user_id),
        tenant_id=tenant_id,
        role=role,
    )
    refresh_token = create_refresh_token(user_id=str(user_id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token_payload: dict) -> TokenResponse:
    """Refresh an access token using a valid refresh token.

    Expects a JSON body with a 'refresh_token' field. Validates the
    refresh token, checks the user exists and is active, then issues
    a new access token with the user's current tenantId and role.
    """
    token = refresh_token_payload.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refresh_token is required",
        )

    # --- Validate refresh token ---
    try:
        payload = verify_token(token, expected_type="refresh")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Invalid or expired refresh token",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    # --- Fetch user ---
    users_collection = get_collection("users")
    user_doc = await users_collection.find_one({"_id": UUID(user_id)})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user_doc.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # --- Fetch membership for tenantId and role ---
    memberships_collection = get_collection("memberships")
    membership_doc = await memberships_collection.find_one({"userId": UUID(user_id)})
    tenant_id = str(membership_doc["tenantId"]) if membership_doc else ""
    role = membership_doc.get("role", "worker") if membership_doc else "worker"

    # --- Generate new tokens ---
    new_access_token = create_access_token(
        user_id=str(user_id),
        tenant_id=tenant_id,
        role=role,
    )
    new_refresh_token = create_refresh_token(user_id=str(user_id))

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserPublic)
async def get_me(
    current_user: UserInDB = Depends(get_current_user),
) -> UserPublic:
    """Get the current authenticated user's profile.

    RLS enforced: the user data is scoped to their tenantId via the
    JWT token validation in the get_current_user dependency.
    """
    return UserPublic(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        tenant_id=str(current_user.tenant_id) if current_user.tenant_id else None,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
    )
