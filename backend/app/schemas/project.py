from pydantic import BaseModel
from typing import Optional, List


class ProjectCreate(BaseModel):
    name: str
    client: Optional[str] = None
    status: str = "Active"
    priority: str = "Medium"
    billable: bool = True
    hourly_rate: Optional[float] = None
    budget_hours: Optional[float] = None
    budget_amount: Optional[float] = None
    deadline: Optional[str] = None
    owner_id: Optional[int] = None


class ProjectUpdate(ProjectCreate):
    name: Optional[str] = None


class ProjectOut(BaseModel):
    id: int
    name: str
    client: Optional[str]
    status: str
    priority: str
    billable: bool
    hourly_rate: Optional[float]
    budget_hours: Optional[float]
    budget_amount: Optional[float]
    deadline: Optional[str]
    owner_id: Optional[int]

    model_config = {"from_attributes": True}


class ProjectBudgetOut(BaseModel):
    project_id: int
    name: str
    budget_hours: Optional[float]
    logged_hours: float
    billable_hours: float
    burned_pct: Optional[float]
    remaining_hours: Optional[float]


class AssignmentCreate(BaseModel):
    user_id: int
    role: Optional[str] = None
    rate: Optional[float] = None
