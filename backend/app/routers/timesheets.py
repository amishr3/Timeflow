from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.database import get_db
from app.models.timesheet import TimeEntry, Timesheet
from app.models.user import User
from app.schemas.timesheet import (
    TeamTimesheetOut,
    TimeEntryCreate,
    TimeEntryOut,
    TimeEntryUpdate,
    TimesheetOut,
    TimesheetStatusUpdate,
)

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


def _get_or_create_timesheet(db: Session, user_id: int, week_start: date) -> Timesheet:
    ts = db.query(Timesheet).filter(
        Timesheet.user_id == user_id,
        Timesheet.week_start == week_start,
    ).first()
    if not ts:
        ts = Timesheet(user_id=user_id, week_start=week_start, status="draft")
        db.add(ts)
        db.commit()
        db.refresh(ts)
    return ts


@router.get("/", response_model=TimesheetOut)
def get_my_timesheet(
    week_start: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ts = _get_or_create_timesheet(db, current_user.id, week_start)
    return ts


@router.post("/entries", response_model=TimeEntryOut, status_code=status.HTTP_201_CREATED)
def log_time(
    payload: TimeEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Find or create the timesheet for that week (Monday)
    week_start = payload.date - __import__("datetime").timedelta(days=payload.date.weekday())
    ts = _get_or_create_timesheet(db, current_user.id, week_start)

    if ts.status in ("submitted", "approved"):
        raise HTTPException(status_code=400, detail="Timesheet already submitted or approved")

    entry = TimeEntry(
        user_id=current_user.id,
        project_id=payload.project_id,
        timesheet_id=ts.id,
        task=payload.task,
        date=payload.date,
        hours=payload.hours,
        billable=payload.billable,
        notes=payload.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/entries/{entry_id}", response_model=TimeEntryOut)
def update_entry(
    entry_id: int,
    payload: TimeEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    ts = db.query(Timesheet).filter(Timesheet.id == entry.timesheet_id).first()
    if ts and ts.status in ("submitted", "approved"):
        raise HTTPException(status_code=400, detail="Cannot edit a submitted timesheet")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(TimeEntry).filter(
        TimeEntry.id == entry_id,
        TimeEntry.user_id == current_user.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()


@router.get("/{timesheet_id}/detail", response_model=TimesheetOut)
def get_timesheet_detail(
    timesheet_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    ts = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    return ts


@router.post("/{timesheet_id}/submit", response_model=TimesheetOut)
def submit_timesheet(
    timesheet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ts = db.query(Timesheet).filter(
        Timesheet.id == timesheet_id,
        Timesheet.user_id == current_user.id,
    ).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if ts.status != "draft":
        raise HTTPException(status_code=400, detail=f"Timesheet is already {ts.status}")

    ts.status = "submitted"
    ts.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ts)
    return ts


@router.post("/{timesheet_id}/approve", response_model=TimesheetOut)
def approve_timesheet(
    timesheet_id: int,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    ts = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if ts.status != "submitted":
        raise HTTPException(status_code=400, detail="Timesheet is not submitted")

    ts.status = "approved"
    ts.reviewed_by = current_user.id
    ts.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ts)
    return ts


@router.post("/{timesheet_id}/reject", response_model=TimesheetOut)
def reject_timesheet(
    timesheet_id: int,
    payload: TimesheetStatusUpdate,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    ts = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not ts:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    if ts.status != "submitted":
        raise HTTPException(status_code=400, detail="Timesheet is not submitted")

    ts.status = "rejected"
    ts.reviewed_by = current_user.id
    ts.reviewed_at = datetime.now(timezone.utc)
    ts.reject_note = payload.reject_note
    db.commit()
    db.refresh(ts)
    return ts


@router.get("/team", response_model=List[TeamTimesheetOut])
def team_timesheets(
    week_start: date,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    team = db.query(User).filter(User.manager_id == current_user.id).all()
    results = []
    for member in team:
        ts = db.query(Timesheet).filter(
            Timesheet.user_id == member.id,
            Timesheet.week_start == week_start,
        ).first()

        total = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.user_id == member.id,
            TimeEntry.date >= week_start,
            TimeEntry.date <= week_start + __import__("datetime").timedelta(days=6),
        ).scalar() or 0.0

        billable = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.user_id == member.id,
            TimeEntry.billable == True,
            TimeEntry.date >= week_start,
            TimeEntry.date <= week_start + __import__("datetime").timedelta(days=6),
        ).scalar() or 0.0

        results.append(TeamTimesheetOut(
            user_id=member.id,
            user_name=member.name,
            user_role=member.team,
            week_start=week_start,
            status=ts.status if ts else "not_started",
            total_hours=total,
            billable_hours=billable,
            timesheet_id=ts.id if ts else None,
        ))
    return results
