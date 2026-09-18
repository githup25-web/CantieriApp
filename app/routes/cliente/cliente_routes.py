from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.cliente import Cliente
from app.models.cliente_access_code import ClienteAccessCode
from app.models.cantiere import Cantiere
from app.security.cliente_auth import (
    ClienteTokenPayload,
    create_cliente_token,
    get_current_cliente,
)

router = APIRouter(prefix="/client", tags=["cliente"])


class ClienteCreateRequest(BaseModel):
    full_name: str
    tenant_id: UUID


class ClienteResponse(BaseModel):
    id: str
    code: str
    full_name: str
    tenant_id: str
    is_active: bool
    created_at: str
    updated_at: str


class ClienteLoginRequest(BaseModel):
    code: str


class ClienteLoginResponse(BaseModel):
    token: str
    cliente_id: str
    cantiere_id: str | None = None


class AssignCantiereRequest(BaseModel):
    cliente_id: UUID
    cantiere_id: UUID


class AssignCantiereResponse(BaseModel):
    status: str
    code: str
    cantiere_id: str


class CantiereAssegnatoResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    status: str


async def _ensure_unique_code(code: str) -> str:
    """Verifica che il codice sia univoco; se non lo è, ne genera un altro."""
    existing = await Cliente.find_one(Cliente.code == code)
    if existing is not None:
        from app.models.cliente import generate_cliente_code

        return await _ensure_unique_code(generate_cliente_code())
    return code


@router.post(
    "/create",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cliente(payload: ClienteCreateRequest) -> ClienteResponse:
    """Crea un nuovo cliente con codice auto-generato."""
    from app.models.cliente import generate_cliente_code

    code = await _ensure_unique_code(generate_cliente_code())

    cliente = Cliente(
        code=code,
        full_name=payload.full_name,
        tenant_id=payload.tenant_id,
    )
    # Assicura che il codice finale sia univoco
    cliente.code = await _ensure_unique_code(code)
    await cliente.insert()

    return ClienteResponse(
        id=str(cliente.id),
        code=cliente.code,
        full_name=cliente.full_name,
        tenant_id=str(cliente.tenant_id),
        is_active=cliente.is_active,
        created_at=cliente.created_at.isoformat(),
        updated_at=cliente.updated_at.isoformat(),
    )


@router.post("/login", response_model=ClienteLoginResponse)
async def client_login(payload: ClienteLoginRequest) -> ClienteLoginResponse:
    """Login cliente tramite codice. Genera un JWT con i dati del cliente."""
    cliente = await Cliente.find_one(Cliente.code == payload.code)
    if not cliente or not cliente.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Codice cliente non valido o disattivato",
        )

    # Trova il cantiere associato (se esiste un access code attivo)
    access = await ClienteAccessCode.find_one(
        {"cliente_id": str(cliente.id), "active": True}
    )
    cantiere_id = access.cantiere_id if access else None

    token = create_cliente_token(str(cliente.id), cantiere_id or "")

    return ClienteLoginResponse(
        token=token,
        cliente_id=str(cliente.id),
        cantiere_id=cantiere_id,
    )


@router.post("/assign-cantiere", response_model=AssignCantiereResponse)
async def assign_cantiere(payload: AssignCantiereRequest) -> AssignCantiereResponse:
    """Assegna un cantiere a un cliente, creando un ClienteAccessCode."""
    cliente = await Cliente.get(payload.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente non trovato")

    cantiere = await Cantiere.get(payload.cantiere_id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere non trovato")

    # Verifica che il cantiere appartenga allo stesso tenant del cliente
    if str(cantiere.organization_id) != str(cliente.tenant_id):
        raise HTTPException(
            status_code=403,
            detail="Il cantiere non appartiene al tenant del cliente",
        )

    # Genera codice di accesso
    from app.routes.cliente.accesso import generate_code

    code = generate_code()

    access = ClienteAccessCode(
        code=code,
        cliente_id=str(cliente.id),
        cantiere_id=str(cantiere.id),
        active=True,
        created_at=datetime.now(timezone.utc),
    )
    await access.insert()

    return AssignCantiereResponse(
        status="assigned",
        code=code,
        cantiere_id=str(cantiere.id),
    )


@router.get("/cantieri", response_model=list[CantiereAssegnatoResponse])
async def get_clienti_cantieri(
    current_cliente: ClienteTokenPayload = Depends(get_current_cliente),
) -> list[CantiereAssegnatoResponse]:
    """Elenca i cantieri assegnati al cliente autenticato."""
    cliente_id = str(current_cliente.cliente_id)

    # Trova tutti gli access code attivi per questo cliente
    access_codes = await ClienteAccessCode.find(
        {"cliente_id": cliente_id, "active": True}
    ).to_list()

    cantieri: list[CantiereAssegnatoResponse] = []
    for access in access_codes:
        cantiere = await Cantiere.get(UUID(access.cantiere_id))
        if cantiere:
            cantieri.append(
                CantiereAssegnatoResponse(
                    id=str(cantiere.id),
                    title=cantiere.title,
                    description=cantiere.description,
                    status=cantiere.status,
                )
            )

    return cantieri
