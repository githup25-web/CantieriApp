"""Rotte per il sistema di inviti (FASE 5).

Endpoint:
- POST   /invite/create           -> Solo admin/owner crea invito
- POST   /invite/accept           -> Pubblico, accetta invito e crea user + membership
- GET    /invite/list             -> Solo admin/owner, lista inviti del tenant
- GET    /invite/verify           -> Pubblico, verifica validità invito (compatibilità)
- DELETE /invite/{inviteId}       -> Solo admin/owner, invalida invito (canceled)

Sicurezza / RLS:
- Ogni query sugli inviti è filtrata per tenantId
- Solo admin/owner del tenant può creare/listare/eliminare inviti
- L'accettazione crea lo user con tenantId dell'admin e invalida l'invito
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from backend.core.database import get_collection
from backend.core.security import get_password_hash
from backend.dependencies.auth import get_current_user
from backend.models.invite import InviteDB
from backend.models.tenant import MembershipDB
from backend.models.user import UserDB, UserInDB
from backend.schemas.invite import (
    InviteAcceptSchema,
    InviteCreateSchema,
    InviteListResponseSchema,
    InviteResponseSchema,
)

router = APIRouter(prefix="/invite", tags=["invites"])

# Ruoli autorizzati a gestire gli inviti
ADMIN_ROLES = ("admin", "owner")


async def _get_admin_tenant(current_user: UserInDB) -> tuple[UUID, str]:
    """Helper RLS: verifica che l'utente sia admin/owner e restituisce tenantId + ruolo.

    Raises:
        HTTPException 403: Se l'utente non è membro o non ha ruolo admin/owner.
    """
    memberships_collection = get_collection("memberships")
    membership = await memberships_collection.find_one({"userId": current_user.id})

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'utente non è membro di alcun tenant",
        )

    role = membership.get("role", "worker")
    if role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin o owner del tenant può gestire gli inviti",
        )

    return membership["tenantId"], role


def _invite_to_response(invite: InviteDB) -> InviteResponseSchema:
    """Converte un documento InviteDB in risposta API pubblica."""
    return InviteResponseSchema(
        id=str(invite.id),
        email=invite.email,
        role=invite.role,
        token=invite.token,
        status=invite.status,
        tenant_id=str(invite.tenant_id),
        created_by=str(invite.created_by),
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
        accepted_by=str(invite.accepted_by) if invite.accepted_by else None,
        canceled_at=invite.canceled_at,
    )


@router.post(
    "/create",
    response_model=InviteResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    payload: InviteCreateSchema,
    current_user: UserInDB = Depends(get_current_user),
) -> InviteResponseSchema:
    """Crea un nuovo invito per un worker o un client (solo admin/owner).

    L'invito viene salvato nel tenant dell'admin (RLS via tenantId).
    Il token è generato come UUID4.
    """
    tenant_id, _ = await _get_admin_tenant(current_user)
    invites_collection = get_collection("invites")
    users_collection = get_collection("users")

    # Verifica che l'utente non esista già nel sistema (email univoca)
    existing_user = await users_collection.find_one({"email": payload.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esiste già un utente con questa email",
        )

    # Verifica che non esista già un invito pending per la stessa email e tenant
    existing = await invites_collection.find_one(
        {"email": payload.email, "tenantId": tenant_id, "status": "pending"}
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esiste già un invito attivo per questa email in questo tenant",
        )

    # Crea l'invito con token UUID4
    invite = InviteDB(
        email=payload.email,
        role=payload.role,
        tenantId=tenant_id,
        createdBy=current_user.id,
    )
    await invites_collection.insert_one(invite.model_dump(by_alias=True))

    return _invite_to_response(invite)


@router.post("/accept", response_model=dict)
async def accept_invite(payload: InviteAcceptSchema) -> dict:
    """Accetta un invito creando user + membership nel tenant dell'admin.

    Endpoint pubblico: l'utente utilizza il token ricevuto via email.
    L'invito viene invalidato dopo l'uso (status=accepted).
    """
    invites_collection = get_collection("invites")
    users_collection = get_collection("users")
    memberships_collection = get_collection("memberships")

    # Trova l'invito per token
    invite_doc = await invites_collection.find_one({"token": payload.token})
    if not invite_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invito non trovato",
        )

    invite = InviteDB(**invite_doc)

    # Controlla lo stato dell'invito
    if invite.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invito già accettato",
        )

    if invite.status == "canceled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invito annullato",
        )

    if invite.is_expired():
        now = datetime.now(timezone.utc)
        await invites_collection.update_one(
            {"_id": invite.id},
            {
                "$set": {
                    "status": "expired",
                    "updatedAt": now,
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invito scaduto",
        )

    # Controlla che l'utente non esista già
    existing_user = await users_collection.find_one({"email": invite.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esiste già un utente con questa email",
        )

    # Crea lo user nel tenant dell'admin
    user = UserDB(
        email=invite.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        tenantId=str(invite.tenant_id),
    )
    await users_collection.insert_one(user.model_dump(by_alias=True))

    # Crea la membership nel tenant dell'admin
    membership = MembershipDB(
        userId=user.id,
        tenantId=invite.tenant_id,
        role=invite.role,
    )
    await memberships_collection.insert_one(membership.model_dump(by_alias=True))

    # Invalida l'invito (status=accepted)
    now = datetime.now(timezone.utc)
    await invites_collection.update_one(
        {"_id": invite.id},
        {
            "$set": {
                "status": "accepted",
                "acceptedAt": now,
                "acceptedBy": user.id,
                "updatedAt": now,
            }
        },
    )

    return {
        "message": "Invito accettato con successo",
        "email": invite.email,
        "role": invite.role,
        "tenant_id": str(invite.tenant_id),
    }


@router.get("/list", response_model=InviteListResponseSchema)
async def list_invites(
    current_user: UserInDB = Depends(get_current_user),
) -> InviteListResponseSchema:
    """Elenca tutti gli inviti del tenant dell'admin (RLS via tenantId)."""
    tenant_id, _ = await _get_admin_tenant(current_user)
    invites_collection = get_collection("invites")

    cursor = invites_collection.find({"tenantId": tenant_id}).sort(
        "createdAt", -1
    )
    invite_docs = await cursor.to_list(length=100)

    items = [_invite_to_response(InviteDB(**doc)) for doc in invite_docs]

    return InviteListResponseSchema(items=items, total=len(items))


@router.get("/verify", response_model=InviteResponseSchema)
async def verify_invite(token: str = Query(...)) -> InviteResponseSchema:
    """Verifica la validità di un invito tramite token (endpoint pubblico).

    Utile per le app Flutter per mostrare lo stato dell'invito prima
    dell'accettazione.
    """
    invites_collection = get_collection("invites")

    invite_doc = await invites_collection.find_one({"token": token})
    if not invite_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invito non trovato",
        )

    invite = InviteDB(**invite_doc)

    if invite.status == "pending" and invite.is_expired():
        await invites_collection.update_one(
            {"_id": invite.id},
            {
                "$set": {
                    "status": "expired",
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invito scaduto",
        )

    return _invite_to_response(invite)


@router.delete("/{invite_id}", response_model=dict)
async def delete_invite(
    invite_id: UUID = Path(...),
    current_user: UserInDB = Depends(get_current_user),
) -> dict:
    """Invalida un invito (status=canceled) — solo admin/owner.

    RLS: l'invito viene cercato con il tenantId dell'admin.
    """
    tenant_id, _ = await _get_admin_tenant(current_user)
    invites_collection = get_collection("invites")

    # RLS: filtro per _id + tenantId
    invite_doc = await invites_collection.find_one(
        {"_id": invite_id, "tenantId": tenant_id}
    )
    if not invite_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invito non trovato",
        )

    invite = InviteDB(**invite_doc)

    if invite.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossibile eliminare un invito già accettato",
        )

    # Invalida l'invito
    now = datetime.now(timezone.utc)
    await invites_collection.update_one(
        {"_id": invite.id},
        {
            "$set": {
                "status": "canceled",
                "canceledAt": now,
                "updatedAt": now,
            }
        },
    )

    return {
        "message": "Invito annullato con successo",
        "invite_id": str(invite.id),
        "status": "canceled",
    }
