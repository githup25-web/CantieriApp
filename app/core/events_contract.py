from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Official domain event names (used as event_name in the dispatcher)
# Keep this list in sync with notification_service mapping.
OFFICIAL_EVENT_NAMES: set[str] = {
    # preventivo
    "preventivo.status_changed",
    "preventivo.pdf_uploaded",
    # fattura
    "fattura.created",
    "fattura.inviata",
    "fattura.pagata",
    "fattura.scaduta",
    # task
    "task.created",
    "task.assigned",
    "task.completed",
    "task.in_late",  # placeholder (naming convention for "in ritardo")
    # cantiere
    "cantiere.created",
    "cantiere.updated",
    "cantiere.status_changed",
    "cantiere.closed",
    # utente
    "user.registered",
    "user.invited",
    "user.activated",
    "user.deactivated",
    # membership / presence / documents / spesa
    "membership.created",
    "presenza.created",
    "documento.uploaded",
    "spesa.created",

    # cliente feedback (used by client workflow)
    "cliente.feedback.received",
    "cliente.feedback.processed",

    # (legacy/extra names observed in current codebase can be added here)
}


class EventEnvelope(BaseModel):
    """
    Standard event contract for CantieriApp.

    Min required fields:
    - event_name
    - entity_type, entity_id
    - organization_id
    - recipient_user_id
    - payload (dict)
    - event_instance_id (optional, used for idempotency logical occurrence)
    """

    event_name: str
    entity_type: str
    entity_id: UUID | str | None = None

    organization_id: UUID | None = None
    recipient_user_id: UUID | None = None

    payload: dict[str, Any] = {}

    # A stable identifier of the logical event occurrence.
    # Best-effort: if producer doesn't have it, we fallback to payload-derived values.
    event_instance_id: str | None = None

    occurred_at: datetime = datetime.now(timezone.utc)

    model_config = ConfigDict(extra="allow")


def normalize_event_context(event_name: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    Make existing (legacy) dispatcher payloads conform to our contract without breaking
    current producers/tests.

    Compatibility expectations (currently used in notification_service/tests):
    - organization_id: UUID | None
    - recipient_user_id: UUID | None
    - entity_id: UUID | str | None
    - data: dict (optional)
    - event_instance_id: optional

    We normalize to:
    - organization_id
    - recipient_user_id
    - entity_id
    - data (always dict)
    - event_instance_id
    - entity_type (best-effort)
    """
    ctx = dict(context or {})
    payload_data = ctx.get("data", {})
    if not isinstance(payload_data, dict):
        payload_data = {}

    # Best-effort entity_type derived from event_name prefix (e.g. "preventivo." -> "preventivo")
    entity_type = ctx.get("entity_type")
    if not entity_type and "." in event_name:
        entity_type = event_name.split(".", 1)[0]
    if entity_type:
        ctx["entity_type"] = entity_type

    ctx["data"] = payload_data

    # Preserve/ensure optional fields
    if "event_instance_id" not in ctx:
        ctx["event_instance_id"] = None

    return ctx
