from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from datetime import datetime


class PaymentCreate(BaseModel):
    user_id: str
    service_id: Optional[str] = None
    property_id: Optional[str] = None
    amount: float
    currency: str = "ARS"
    payment_date: datetime
    due_date: Optional[datetime] = None
    status: Literal["pending", "paid", "overdue"] = "pending"
    period: Optional[str] = None
    input_method: Literal["whatsapp", "manual", "email"] = "manual"
    notes: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    ai_extracted: Optional[dict[str, Any]] = None


class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    payment_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: Optional[Literal["pending", "paid", "overdue"]] = None
    period: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    ai_extracted: Optional[dict[str, Any]] = None


class PaymentResponse(PaymentCreate):
    id: str = Field(alias="_id")
    created_at: datetime

    model_config = {"populate_by_name": True}
