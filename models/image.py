
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"))

    post = relationship("Post", back_populates="images")
