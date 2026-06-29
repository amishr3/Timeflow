from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ExpenseCreate(BaseModel):
    project_id: Optional[int] = None
    date: date
    category: str
    description: str
    amount: float
    billable: bool = False


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    billable: Optional[bool] = None
    project_id: Optional[int] = None


class ExpenseOut(BaseModel):
    id: int
    user_id: int
    project_id: Optional[int]
    date: date
    category: str
    description: str
    amount: float
    billable: bool
    receipt_url: Optional[str]
    status: str
    reject_note: Optional[str]
    reviewed_at: Optional[datetime]
    user_name: Optional[str] = None
    project_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ExpenseReject(BaseModel):
    reject_note: Optional[str] = None
