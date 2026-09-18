from datetime import datetime, timezone
from uuid import UUID, uuid4

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


class OrganizationBase(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True


class OrganizationCreate(OrganizationBase):
    pass


class Organization(Document, OrganizationBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "organizations"

    model_config = ConfigDict(populate_by_name=True)


class OrganizationPublic(OrganizationBase):
    id: str | None = None
