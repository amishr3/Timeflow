from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.database import get_db
from app.models.project import Project
from app.models.timesheet import TimeEntry
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/utilization")
def utilization_report(
    from_date: date,
    to_date: date,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    team = db.query(User).filter(User.manager_id == current_user.id).all()
    results = []
    for member in team:
        total = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.user_id == member.id,
            TimeEntry.date >= from_date,
            TimeEntry.date <= to_date,
        ).scalar() or 0.0

        billable = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.user_id == member.id,
            TimeEntry.billable == True,
            TimeEntry.date >= from_date,
            TimeEntry.date <= to_date,
        ).scalar() or 0.0

        days = (to_date - from_date).days + 1
        weeks = days / 7
        capacity = member.weekly_capacity_hours * weeks
        util = round((billable / capacity) * 100, 1) if capacity else 0.0

        results.append({
            "user_id": member.id,
            "user_name": member.name,
            "total_hours": total,
            "billable_hours": billable,
            "capacity_hours": round(capacity, 1),
            "billable_utilization_pct": util,
            "target_pct": member.billable_target_pct,
            "on_target": util >= member.billable_target_pct,
        })
    return results


@router.get("/projects")
def projects_report(
    from_date: date,
    to_date: date,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    projects = db.query(Project).all()
    results = []
    for p in projects:
        total = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.project_id == p.id,
            TimeEntry.date >= from_date,
            TimeEntry.date <= to_date,
        ).scalar() or 0.0

        billable = db.query(func.sum(TimeEntry.hours)).filter(
            TimeEntry.project_id == p.id,
            TimeEntry.billable == True,
            TimeEntry.date >= from_date,
            TimeEntry.date <= to_date,
        ).scalar() or 0.0

        revenue = round(billable * p.hourly_rate, 2) if p.hourly_rate else None
        burned_pct = round((total / p.budget_hours) * 100, 1) if p.budget_hours else None

        results.append({
            "project_id": p.id,
            "project_name": p.name,
            "status": p.status,
            "total_hours": total,
            "billable_hours": billable,
            "budget_hours": p.budget_hours,
            "burned_pct": burned_pct,
            "estimated_revenue": revenue,
        })
    return results


@router.get("/expenses")
def expenses_report(
    from_date: date,
    to_date: date,
    _: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    from app.models.expense import Expense
    rows = db.query(Expense).filter(
        Expense.date >= from_date,
        Expense.date <= to_date,
    ).all()

    total      = sum(e.amount for e in rows)
    approved   = sum(e.amount for e in rows if e.status == "approved")
    billable   = sum(e.amount for e in rows if e.billable and e.status == "approved")
    by_category: dict = {}
    for e in rows:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount

    return {
        "total_submitted": round(total, 2),
        "total_approved": round(approved, 2),
        "total_billable": round(billable, 2),
        "count": len(rows),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }
