from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False)
    client         = Column(String, nullable=True)
    status         = Column(String, default="Active")
    priority       = Column(String, default="Medium")
    billable       = Column(Boolean, default=True)
    hourly_rate    = Column(Float, nullable=True)
    budget_hours   = Column(Float, nullable=True)
    budget_amount  = Column(Float, nullable=True)
    deadline       = Column(String, nullable=True)
    owner_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    owner           = relationship("User", back_populates="owned_projects")
    assignments     = relationship("ProjectAssignment", back_populates="project")
    time_entries    = relationship("TimeEntry", back_populates="project")
    allocations     = relationship("Allocation", back_populates="project")
    expenses        = relationship("Expense", back_populates="project")


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    role        = Column(String, nullable=True)
    rate        = Column(Float, nullable=True)

    project = relationship("Project", back_populates="assignments")
    user    = relationship("User")
