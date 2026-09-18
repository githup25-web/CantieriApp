from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from beanie import Document


class ClienteFeedback(Document):
    """
    Feedback inviato da un cliente per un cantiere.
    Vincoli di business:
    - NON deve mai causare chiusura cantiere
    - NON deve mai disattivare codici cliente
    """

    cliente_id: str
    cantiere_id: str

    # Dati di compilazione
    questionnaire: dict[str, Any] = {}

    testimony: Optional[str] = None
    social: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    class Settings:
        name = "cliente_feedbacks"
