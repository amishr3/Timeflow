from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "employee"
    team: Optional[str] = None
    weekly_capacity_hours: float = 40.0
    billable_target_pct: float = 80.0
    manager_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    team: Optional[str]
    weekly_capacity_hours: float
    billable_target_pct: float
    manager_id: Optional[int]

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    team: Optional[str] = None
    weekly_capacity_hours: Optional[float] = None
    billable_target_pct: Optional[float] = None
    manager_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
