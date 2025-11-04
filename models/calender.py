from sqlalchemy import Column, DateTime, func, ForeignKey
from sqlalchemy import Integer

from database import Base


class Stamps(Base):
    __tablename__ = "Stamps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, default=func.now())
    stamp_lev = Column(Integer)

    user_id = Column(Integer, ForeignKey("users.id"))

    