from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.cliente_access_code import ClienteAccessCode
from app.routes.organization import check_role
from app.models.cantiere import Cantiere

router = APIRouter(prefix="/cliente", tags=["cliente"])


def generate_code() -> str:
    # Esempio: CANT-482991 (codice permanente)
    # Nota: per ora semplice; puoi sostituire con un generatore più robusto se necessario.
    import random

    digits = random.randint(0, 999999)
    return f"CANT-{digits:06d}"


class GeneraCodiceIn(BaseModel):
    cliente_id: str
    cantiere_id: str


@router.post("/accesso/genera")
async def genera_codice(
    body: GeneraCodiceIn,
    _current_user=Depends(check_role(["owner", "admin", "manager"])),
):
    # Richiesta: genera codice permanente e associato cliente <-> cantiere
    code = generate_code()

    # opzionale: verifica che il cantiere esista
    cantiere = await Cantiere.find_one(Cantiere.id == UUID(body.cantiere_id))
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere non trovato")

    # salva codice
    access = ClienteAccessCode(
        code=code,
        cliente_id=body.cliente_id,
        cantiere_id=str(cantiere.id),
        active=True,
        created_at=datetime.now(timezone.utc),
    )
    await access.insert()
    return {"code": code}


class LoginCodiceIn(BaseModel):
    code: str


@router.post("/accesso/login")
async def login_codice(body: LoginCodiceIn):
    access = await ClienteAccessCode.find_one(
        (ClienteAccessCode.code == body.code) & (ClienteAccessCode.active == True)  # noqa: E712
    )

    if not access:
        raise HTTPException(status_code=401, detail="Codice non valido o disattivato")

    # JWT minimale cliente
    from app.security.cliente_auth import create_cliente_token

    token = create_cliente_token(access.cliente_id, access.cantiere_id)
    return {"token": token}


class DisattivaCodiceOut(BaseModel):
    status: str
