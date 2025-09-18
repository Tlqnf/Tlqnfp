from sqlalchemy import Column, Integer, Boolean, String, Text, ForeignKey, DateTime, func, Float, ARRAY
from sqlalchemy.orm import relationship
from database import Base
import enum
from .image import Image


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    like_count = Column(Integer, default=0)
    read_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    hash_tag = Column(ARRAY(String(10)), nullable=True)
    public = Column(Boolean, default=False)

    speed = Column(Float)
    distance = Column(Float)
    time = Column(DateTime(timezone=True))

    author = relationship("User", back_populates="posts")
    report = relationship("Report", back_populates="posts")
    comments = relationship(
        "Comment",
        primaryjoin="and_(Post.id == Comment.post_id, Comment.parent_id == None)",
        back_populates="post", 
        cascade="all, delete-orphan"
    )
    images = relationship("Image", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Self-referential relationship for nested comments
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    parent = relationship("Comment", remote_side=[id], back_populates="children")
    children = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
    mentions = relationship("Mention", back_populates="comment", cascade="all, delete-orphan")

    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    report = relationship("Report", back_populates="comments")
