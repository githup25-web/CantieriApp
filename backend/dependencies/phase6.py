from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status

from backend.core.database import get_collection
from backend.dependencies.auth import get_current_user
from backend.models.user import UserInDB

ADMIN_ROLES = frozenset({"admin", "owner"})
WORKER_ROLES = ADMIN_ROLES | {"worker"}


@dataclass(frozen=True, slots=True)
class TenantContext:
    """Utente autenticato, tenant attivo e ruolo verificato dalla membership."""

    user: UserInDB
    tenant_id: UUID
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES


async def get_tenant_context(
    current_user: UserInDB = Depends(get_current_user),
) -> TenantContext:
    """Conferma che l'utente appartenga al tenant indicato nel suo profilo."""

    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no active tenant",
        )

    try:
        tenant_id = UUID(current_user.tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has an invalid tenant",
        ) from exc

    memberships_collection = get_collection("memberships")
    membership = await memberships_collection.find_one(
        {"userId": current_user.id, "tenantId": tenant_id}
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of the active tenant",
        )

    return TenantContext(
        user=current_user,
        tenant_id=tenant_id,
        role=membership.get("role", "worker"),
    )


async def require_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Consente l'accesso solo ad admin e owner del tenant corrente."""

    if not context.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return context


async def require_worker_or_admin(
    context: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Consente le operazioni riservate a worker, admin e owner."""

    if context.role not in WORKER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker role required",
        )
    return context