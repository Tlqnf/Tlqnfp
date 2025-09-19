from sqlalchemy import Column, Integer, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 알림 받을 유저
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    type = Column(String, nullable=False)  # "mention", "like", "follow" 등
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
    comment = relationship("Comment")

class Mention(Base):
    __tablename__ = "mentions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 멘션된 유저
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    comment = relationship("Comment", back_populates="mentions")
    user = relationship("User", back_populates="mentions")
