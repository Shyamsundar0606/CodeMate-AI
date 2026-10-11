import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserPage(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int
