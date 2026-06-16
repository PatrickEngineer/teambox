from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default="todo")
    priority = Column(String, default="medium")
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="check_status"),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="check_priority"),
    )