from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    name: str
    phone: str
    locale: str = "es-AR"


class UserResponse(UserCreate):
    id: str
    created_at: datetime

    model_config = {"populate_by_name": True}
