from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ExpenseCreate(BaseModel):
    """Schema for creating a new expense."""
    cantiere_id: UUID
    category: str
    amount: float
    description: str
    receipt_url: str | None = None


class ExpenseDB(BaseModel):
    """MongoDB document structure for expenses collection."""
    id: UUID = Field(default_factory=uuid4, alias="_id")
    user_id: UUID
    tenant_id: UUID
    cantiere_id: UUID
    category: str
    amount: float
    description: str
    receipt_url: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        json_encoders = {UUID: str}


class ExpensePublic(BaseModel):
    """Public expense data returned by API."""
    id: str
    user_id: str
    tenant_id: str
    cantiere_id: str
    category: str
    amount: float
    description: str
    receipt_url: str | None = None
    timestamp: str
