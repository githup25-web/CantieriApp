from __future__ import annotations

from beanie import Document
from datetime import datetime
from typing import Any, Dict, List, Optional


class WorkflowInstance(Document):
    workflow_name: str
    context: Dict[str, Any]
    state: str  # pending, running, waiting, done, error
    current_step: int
    steps: List[str]
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None
