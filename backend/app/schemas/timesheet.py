from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class TimeEntryCreate(BaseModel):
    project_id: int
    task: Optional[str] = None
    date: date
    hours: float
    billable: bool = True
    notes: Optional[str] = None


class TimeEntryUpdate(BaseModel):
    task: Optional[str] = None
    hours: Optional[float] = None
    billable: Optional[bool] = None
    notes: Optional[str] = None


class TimeEntryOut(BaseModel):
    id: int
    user_id: int
    project_id: int
    timesheet_id: Optional[int]
    task: Optional[str]
    date: date
    hours: float
    billable: bool
    notes: Optional[str]

    model_config = {"from_attributes": True}


class TimesheetOut(BaseModel):
    id: int
    user_id: int
    week_start: date
    status: str
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reject_note: Optional[str]
    entries: List[TimeEntryOut] = []

    model_config = {"from_attributes": True}


class TimesheetStatusUpdate(BaseModel):
    reject_note: Optional[str] = None


class TeamTimesheetOut(BaseModel):
    user_id: int
    user_name: str
    user_role: Optional[str]
    week_start: date
    status: str
    total_hours: float
    billable_hours: float
    timesheet_id: Optional[int]
