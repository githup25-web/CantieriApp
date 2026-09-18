from __future__ import annotations

from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.cliente_access_code import ClienteAccessCode
from app.routes.organization import check_role

router = APIRouter(prefix="/admin", tags=["admin"])


class DisattivaCodiceIn(BaseModel):
    code: str


@router.post("/cliente/disattiva_codice")
async def disattiva_codice(
    body: DisattivaCodiceIn,
    _current_user=Depends(check_role(["owner", "admin", "manager"])),
):
    access = await ClienteAccessCode.find_one(ClienteAccessCode.code == body.code)
    if not access:
        raise HTTPException(status_code=404, detail="Codice non trovato")

    access.active = False
    access.deactivated_at = datetime.now(timezone.utc)
    await access.save()
    return {"status": "codice_disattivato"}
