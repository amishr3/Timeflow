from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_current_user, require_manager
from app.database import get_db
from app.models.allocation import Allocation
from app.models.project import Project, ProjectAssignment
from app.models.timesheet import TimeEntry
from app.models.user import User
from app.schemas.project import AssignmentCreate, ProjectBudgetOut, ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "manager":
        return db.query(Project).all()
    # Employees see projects they're explicitly assigned to OR have allocations for
    assigned_ids  = db.query(ProjectAssignment.project_id).filter(ProjectAssignment.user_id == current_user.id)
    allocated_ids = db.query(Allocation.project_id).filter(Allocation.user_id == current_user.id)
    all_ids = assigned_ids.union(allocated_ids).subquery()
    return db.query(Project).filter(Project.id.in_(all_ids)).all()


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()


@router.get("/{project_id}/budget", response_model=ProjectBudgetOut)
def project_budget(
    project_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    total = db.query(func.sum(TimeEntry.hours)).filter(TimeEntry.project_id == project_id).scalar() or 0.0
    billable = db.query(func.sum(TimeEntry.hours)).filter(
        TimeEntry.project_id == project_id, TimeEntry.billable == True
    ).scalar() or 0.0

    burned_pct = round((total / project.budget_hours) * 100, 1) if project.budget_hours else None
    remaining  = round(project.budget_hours - total, 1) if project.budget_hours else None

    return ProjectBudgetOut(
        project_id=project.id,
        name=project.name,
        budget_hours=project.budget_hours,
        logged_hours=total,
        billable_hours=billable,
        burned_pct=burned_pct,
        remaining_hours=remaining,
    )


@router.post("/{project_id}/assign", status_code=status.HTTP_201_CREATED)
def assign_member(
    project_id: int,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager),
):
    existing = db.query(ProjectAssignment).filter(
        ProjectAssignment.project_id == project_id,
        ProjectAssignment.user_id == payload.user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already assigned")

    assignment = ProjectAssignment(
        project_id=project_id,
        user_id=payload.user_id,
        role=payload.role,
        rate=payload.rate,
    )
    db.add(assignment)
    db.commit()
    return {"detail": "Assigned"}
