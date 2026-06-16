from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint
from app.database import Base


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    role = Column(String, default="member")

    __table_args__ = (
        UniqueConstraint('user_id', 'project_id', name='unique_user_project'),
    )