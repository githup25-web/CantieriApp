from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.cantiere import Cantiere
from app.models.cliente_access_code import ClienteAccessCode
from app.routes.organization import check_role

router = APIRouter(prefix="/admin", tags=["admin"])


class ChiudiCantiereIn(BaseModel):
    cantiere_id: UUID


@router.post("/cantiere/chiudi")
async def chiudi_cantiere(
    body: ChiudiCantiereIn,
    _current_user=Depends(check_role(["owner", "admin", "manager"])),
):
    cantiere = await Cantiere.find_one(Cantiere.id == body.cantiere_id)
    if not cantiere:
        raise HTTPException(status_code=404, detail="Cantiere non trovato")

    cantiere.status = "closed"
    cantiere.updated_at = datetime.now(timezone.utc)
    await cantiere.save()

    # disattiva tutti i codici del cantiere
    now = datetime.now(timezone.utc)
    codes = await ClienteAccessCode.find(ClienteAccessCode.cantiere_id == str(cantiere.id)).to_list()
    for c in codes:
        c.active = False
        c.deactivated_at = now
    # Beanie requires per-document save
    for c in codes:
        await c.save()

    return {"status": "cantiere_chiuso"}
