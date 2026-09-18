from datetime import datetime
from typing import Optional

from beanie import Document


class ClienteAccessCode(Document):
    code: str
    cliente_id: str
    cantiere_id: str
    active: bool = True
    created_at: datetime
    deactivated_at: Optional[datetime] = None
