from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Allocation(Base):
    __tablename__ = "allocations"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "week_start", name="uq_allocation"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False)
    week_start   = Column(Date, nullable=False)
    planned_hours= Column(Float, default=0.0)
    billable     = Column(Boolean, default=True)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user    = relationship("User", back_populates="allocations")
    project = relationship("Project", back_populates="allocations")
