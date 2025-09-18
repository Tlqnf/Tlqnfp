from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

bookmarked_routes = Table(
    'bookmarked_routes',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('route_id', Integer, ForeignKey('routes.id'), primary_key=True)
)

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
    bookmarked_by_users = relationship(
        "User",
        secondary=bookmarked_routes,
        back_populates="bookmarked_routes"
    )
