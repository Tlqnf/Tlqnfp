from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    username = Column(String(100), nullable=False)
    profile_description = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)

    google_id = Column(String, unique=True, nullable=True)
    naver_id = Column(String, unique=True, nullable=True)
    kakao_id = Column(String, unique=True, nullable=True)

    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")
    reports = relationship("Report", back_populates="author")
    routes = relationship("Route", back_populates="author")
    bookmarked_routes = relationship(
        "Route",
        secondary="bookmarked_routes",
        back_populates="bookmarked_by_users"
    )
