from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.events import dispatcher
from app.models.cantiere import Cantiere
from app.models.cliente_feedback import ClienteFeedback
from app.models.membership import Membership
from app.models.notification import Notification
from app.workflow.engine import register_workflow, emit_event


@register_workflow("cliente.feedback")
async def cliente_feedback(context: dict[str, Any]) -> dict[str, Any]:
    """
    Workflow cliente.feedback
    Vincoli:
    - NON deve chiudere il cantiere
    - NON deve disattivare codici cliente
    """

    feedback_id = context.get("feedback_id")
    cliente_id = context.get("cliente_id")
    cantiere_id = context.get("cantiere_id")

    # Validazione minima
    if not feedback_id or not cliente_id or not cantiere_id:
        raise ValueError("Missing required workflow context: feedback_id/cliente_id/cantiere_id")

    # 1) Richiesta task: emetti anche l'evento "ricevuto"
    await emit_event(
        "cliente.feedback.received",
        {"feedback_id": feedback_id, "cliente_id": cliente_id, "cantiere_id": cantiere_id},
    )

    # 2) Richiesta task: notifica interna admin/soci/capi (nessuna chiusura cantiere)
    #    Creiamo direttamente Notification (non via notification_service generico),
    #    così possiamo limitare i ruoli.
    cantiere_uuid = UUID(str(cantiere_id))

    cantiere = await Cantiere.find_one(Cantiere.id == cantiere_uuid)
    if cantiere is None:
        # best-effort: se cantiere mancante non blocchiamo il workflow
        pass
    else:
        organization_id = cantiere.organization_id

        allowed_roles = {"admin", "socio", "capi"}

        memberships = await Membership.find(
            Membership.organization_id == organization_id,
        ).to_list()

        role_recipients = [
            m.user_id
            for m in memberships
            if m.role in allowed_roles and getattr(m, "user_id", None) is not None
        ]

        # dedupe
        recipients = []
        seen: set[UUID] = set()
        for rid in role_recipients:
            if rid in seen:
                continue
            seen.add(rid)
            recipients.append(rid)

        # Idempotency: use event/feedback as deterministic idempotency_key.
        for rid in recipients:
            notif = Notification(
                recipient_user_id=rid,
                organization_id=organization_id,
                type="cliente.feedback.received",
                entity_id=str(feedback_id),
                idempotency_key=f"cliente.feedback.received|r={rid}|f={feedback_id}",
                payload={
                    "feedback_id": str(feedback_id),
                    "cliente_id": str(cliente_id),
                    "cantiere_id": str(cantiere_id),
                },
                is_read=False,
            )
            try:
                await notif.insert()
            except Exception:
                # duplicate or race => ignore
                pass

    # 3) Manteniamo anche evento processed (già presente in precedenza)
    await emit_event(
        "cliente.feedback.processed",
        {"feedback_id": feedback_id, "cliente_id": cliente_id, "cantiere_id": cantiere_id},
    )

    return {
        "status": "feedback_processed",
        "feedback_id": feedback_id,
        "cliente_id": cliente_id,
        "cantiere_id": cantiere_id,
    }
