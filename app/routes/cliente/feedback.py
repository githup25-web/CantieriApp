from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models.cliente_feedback import ClienteFeedback
from app.security.cliente_auth import get_current_cliente

router = APIRouter(prefix="/cliente", tags=["cliente"])


class ClienteFeedbackIn(BaseModel):
    questionnaire: dict[str, Any] = {}
    testimony: Optional[str] = None
    social: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@router.post("/feedback")
async def submit_cliente_feedback(
    body: ClienteFeedbackIn,
    current_cliente=Depends(get_current_cliente),
) -> dict[str, str]:
    # Sicurezza:
    # - nessun cantiere_id viene fornito dal client
    # - cantiere_id è preso SOLO dal token (current_cliente)
    fb = ClienteFeedback(
        cliente_id=str(current_cliente.cliente_id),
        cantiere_id=str(current_cliente.cantiere_id),
        questionnaire=body.questionnaire or {},
        testimony=body.testimony,
        social=body.social,
        comment=body.comment,
        metadata=body.metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await fb.insert()

    # Workflow side effects:
    # - NON chiude cantiere
    # - NON disattiva codici
    # (qui lasciamo al workflow la logica di eventuale processamento)
    from app.workflow.engine import emit_event

    await emit_event(
        "cliente.feedback.created",
        {"feedback_id": str(fb.id), "cliente_id": fb.cliente_id, "cantiere_id": fb.cantiere_id},
    )

    # Avvia anche il workflow esplicito "cliente.feedback"
    from app.workflow.engine import start_workflow

    await start_workflow(
        "cliente.feedback",
        {"feedback_id": str(fb.id), "cliente_id": fb.cliente_id, "cantiere_id": fb.cantiere_id},
    )

    return {"status": "received", "feedback_id": str(fb.id)}
