from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id                      = Column(Integer, primary_key=True, index=True)
    name                    = Column(String, nullable=False)
    email                   = Column(String, unique=True, index=True, nullable=False)
    hashed_password         = Column(String, nullable=False)
    role                    = Column(String, default="employee")  # employee | manager
    team                    = Column(String, nullable=True)
    weekly_capacity_hours   = Column(Float, default=40.0)
    billable_target_pct     = Column(Float, default=80.0)
    manager_id              = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())

    manager         = relationship("User", remote_side=[id], backref="reports")
    time_entries    = relationship("TimeEntry", back_populates="user", foreign_keys="TimeEntry.user_id")
    timesheets      = relationship("Timesheet", back_populates="user", foreign_keys="Timesheet.user_id")
    allocations     = relationship("Allocation", back_populates="user")
    expenses        = relationship("Expense", back_populates="user", foreign_keys="Expense.user_id")
    owned_projects  = relationship("Project", back_populates="owner")
