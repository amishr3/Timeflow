from pydantic import BaseModel
from typing import List
from datetime import date


class AllocationItem(BaseModel):
    project_id: int
    planned_hours: float
    billable: bool = True


class AllocationUpsert(BaseModel):
    user_id: int
    week_start: date
    allocations: List[AllocationItem]


class AllocationOut(BaseModel):
    id: int
    user_id: int
    project_id: int
    project_name: str
    week_start: date
    planned_hours: float
    billable: bool

    model_config = {"from_attributes": True}


class MemberAllocationOut(BaseModel):
    user_id: int
    user_name: str
    user_role: str
    capacity: float
    week_start: date
    allocations: List[AllocationOut]
    total_planned: float
    utilization_pct: float
