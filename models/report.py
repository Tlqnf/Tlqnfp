from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func, Float
from sqlalchemy.orm import relationship
from database import Base

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    health_time = Column(Integer, default=0)
    half_time = Column(Integer, default=0)
    distance = Column(Integer, default=0)
    kcal = Column(Integer, default=0)
    average_speed = Column(Float, default=0)
    highest_speed = Column(Float, default=0)
    average_face = Column(Float, default=0)
    highest_face = Column(Float, default=0)
    cumulative_high = Column(Integer, default= 0)
    highest_high = Column(Integer, default=0)
    lowest_high = Column(Integer, default=0)
    increase_slope = Column(Float, default=0)
    decrease_slope = Column(Float, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))
    route_id = Column(Integer, ForeignKey("routes.id"))

    route = relationship("Route", back_populates="reports")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    author = relationship("User", back_populates="reports")
    comments = relationship("Comment", back_populates="report", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="report", cascade="all, delete-orphan")
