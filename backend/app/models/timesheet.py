from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False)
    timesheet_id = Column(Integer, ForeignKey("timesheets.id"), nullable=True)
    task         = Column(String, nullable=True)
    date         = Column(Date, nullable=False)
    hours        = Column(Float, nullable=False, default=0.0)
    billable     = Column(Boolean, default=True)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    user      = relationship("User", back_populates="time_entries")
    project   = relationship("Project", back_populates="time_entries")
    timesheet = relationship("Timesheet", back_populates="entries")


class Timesheet(Base):
    __tablename__ = "timesheets"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start   = Column(Date, nullable=False)   # always a Monday
    status       = Column(String, default="draft")  # draft | submitted | approved | rejected
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at  = Column(DateTime(timezone=True), nullable=True)
    reject_note  = Column(Text, nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship("User", foreign_keys=[user_id], back_populates="timesheets")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    entries  = relationship("TimeEntry", back_populates="timesheet")
