from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_manager
from app.database import get_db
from app.models.expense import Expense
from app.models.project import Project
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseOut, ExpenseReject, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])


def _serialize(e: Expense, db: Session) -> ExpenseOut:
    project = db.query(Project).filter(Project.id == e.project_id).first() if e.project_id else None
    user    = db.query(User).filter(User.id == e.user_id).first()
    return ExpenseOut(
        id=e.id, user_id=e.user_id, project_id=e.project_id,
        date=e.date, category=e.category, description=e.description,
        amount=e.amount, billable=e.billable, receipt_url=e.receipt_url,
        status=e.status, reject_note=e.reject_note, reviewed_at=e.reviewed_at,
        user_name=user.name if user else None,
        project_name=project.name if project else None,
    )


@router.get("/", response_model=List[ExpenseOut])
def my_expenses(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Expense).filter(Expense.user_id == current_user.id)
    if status_filter:
        q = q.filter(Expense.status == status_filter)
    return [_serialize(e, db) for e in q.order_by(Expense.date.desc()).all()]


@router.post("/", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = Expense(
        user_id=current_user.id,
        **payload.model_dump(),
        status="draft",
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return _serialize(expense, db)


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft expenses can be edited")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return _serialize(expense, db)


@router.post("/{expense_id}/submit", response_model=ExpenseOut)
def submit_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "draft":
        raise HTTPException(status_code=400, detail=f"Expense is already {expense.status}")

    expense.status = "submitted"
    db.commit()
    db.refresh(expense)
    return _serialize(expense, db)


@router.post("/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(
    expense_id: int,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "submitted":
        raise HTTPException(status_code=400, detail="Expense is not submitted")

    expense.status = "approved"
    expense.reviewed_by = current_user.id
    expense.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(expense)
    return _serialize(expense, db)


@router.post("/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense(
    expense_id: int,
    payload: ExpenseReject,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "submitted":
        raise HTTPException(status_code=400, detail="Expense is not submitted")

    expense.status = "rejected"
    expense.reviewed_by = current_user.id
    expense.reviewed_at = datetime.now(timezone.utc)
    expense.reject_note = payload.reject_note
    db.commit()
    db.refresh(expense)
    return _serialize(expense, db)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.user_id == current_user.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status == "approved":
        raise HTTPException(status_code=400, detail="Cannot delete an approved expense")
    db.delete(expense)
    db.commit()


@router.get("/team", response_model=List[ExpenseOut])
def team_expenses(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    team_ids = [u.id for u in db.query(User).filter(User.manager_id == current_user.id).all()]
    q = db.query(Expense).filter(Expense.user_id.in_(team_ids))
    if status_filter:
        q = q.filter(Expense.status == status_filter)
    return [_serialize(e, db) for e in q.order_by(Expense.date.desc()).all()]
