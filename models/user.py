from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    profile_description = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)
    fcm_token = Column(String, nullable=True) # For FCM push notifications
    fcm_token_updated_at = Column(DateTime(timezone=True), nullable=True)

    google_id = Column(String, unique=True, nullable=True)
    naver_id = Column(String, unique=True, nullable=True)
    kakao_id = Column(String, unique=True, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="author", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="author", cascade="all, delete-orphan")
    bookmarked_posts = relationship(
        "Post",
        secondary="bookmarked_posts",
        back_populates="bookmarked_by_users"
    )
    liked_posts = relationship(
        "Post",
        secondary="post_likes",
        back_populates="liked_by_users"
    )
    liked_comments = relationship(
        "Comment",
        secondary="comment_likes",
        back_populates="liked_by_users"
    )
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="user", cascade="all, delete-orphan")
