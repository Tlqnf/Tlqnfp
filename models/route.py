from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    start_point = Column(JSONB, nullable=True)
    end_point = Column(JSONB, nullable=True)
    points_json = Column(JSONB)  # 보정된 좌표들을 저장할 JSONB 필드


    author = relationship("User", back_populates="routes")
    reports = relationship("Report", back_populates="route", cascade="all, delete-orphan")