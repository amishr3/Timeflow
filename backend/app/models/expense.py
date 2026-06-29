from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=True)
    date         = Column(Date, nullable=False)
    category     = Column(String, nullable=False)  # Travel | Meals | Software | Equipment | Office | Other
    description  = Column(String, nullable=False)
    amount       = Column(Float, nullable=False)
    billable     = Column(Boolean, default=False)
    receipt_url  = Column(String, nullable=True)
    status       = Column(String, default="draft")  # draft | submitted | approved | rejected
    reject_note  = Column(Text, nullable=True)
    reviewed_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at  = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship("User", foreign_keys=[user_id], back_populates="expenses")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    project  = relationship("Project", back_populates="expenses")
