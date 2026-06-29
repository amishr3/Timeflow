from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.database import get_db
from app.models.allocation import Allocation
from app.models.project import Project
from app.models.user import User
from app.schemas.allocation import AllocationOut, AllocationUpsert, MemberAllocationOut

router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get("/me", response_model=List[AllocationOut])
def my_allocations(
    week_start: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Allocation).filter(
        Allocation.user_id == current_user.id,
        Allocation.week_start == week_start,
    ).all()
    result = []
    for r in rows:
        project = db.query(Project).filter(Project.id == r.project_id).first()
        result.append(AllocationOut(
            id=r.id,
            user_id=r.user_id,
            project_id=r.project_id,
            project_name=project.name if project else "Unknown",
            week_start=r.week_start,
            planned_hours=r.planned_hours,
            billable=r.billable,
        ))
    return result


@router.get("/team", response_model=List[MemberAllocationOut])
def team_allocations(
    week_start: date,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    team = db.query(User).filter(User.manager_id == current_user.id).all()
    results = []
    for member in team:
        rows = db.query(Allocation).filter(
            Allocation.user_id == member.id,
            Allocation.week_start == week_start,
        ).all()

        alloc_out = []
        total = 0.0
        for r in rows:
            project = db.query(Project).filter(Project.id == r.project_id).first()
            alloc_out.append(AllocationOut(
                id=r.id,
                user_id=r.user_id,
                project_id=r.project_id,
                project_name=project.name if project else "Unknown",
                week_start=r.week_start,
                planned_hours=r.planned_hours,
                billable=r.billable,
            ))
            total += r.planned_hours

        util = round((total / member.weekly_capacity_hours) * 100, 1) if member.weekly_capacity_hours else 0.0
        results.append(MemberAllocationOut(
            user_id=member.id,
            user_name=member.name,
            user_role=member.team or "",
            capacity=member.weekly_capacity_hours,
            week_start=week_start,
            allocations=alloc_out,
            total_planned=total,
            utilization_pct=util,
        ))
    return results


@router.put("/", response_model=List[AllocationOut])
def upsert_allocations(
    payload: AllocationUpsert,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Replace all allocations for a user+week with the given list."""
    db.query(Allocation).filter(
        Allocation.user_id == payload.user_id,
        Allocation.week_start == payload.week_start,
    ).delete()

    result = []
    for item in payload.allocations:
        project = db.query(Project).filter(Project.id == item.project_id).first()
        alloc = Allocation(
            user_id=payload.user_id,
            project_id=item.project_id,
            week_start=payload.week_start,
            planned_hours=item.planned_hours,
            billable=item.billable,
        )
        db.add(alloc)
        db.flush()
        result.append(AllocationOut(
            id=alloc.id,
            user_id=alloc.user_id,
            project_id=alloc.project_id,
            project_name=project.name if project else "Unknown",
            week_start=alloc.week_start,
            planned_hours=alloc.planned_hours,
            billable=alloc.billable,
        ))

    db.commit()
    return result
