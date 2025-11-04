from datetime import datetime
from idlelib.query import Query
from typing import Any

from sqlalchemy.sql.expression import extract

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.calender import Stamps
from schemas.calender import StampRecord, CalenderStampData, StampCount


def getStampData(db: Session, user_id: int, is_day: bool, date: datetime = datetime.today())-> list[type[CalenderStampData]] | \
                                                                                               list[Any] | None | Any:
    if(is_day):
        return db.query(Stamps).filter(
            Stamps.user_id == user_id,
            extract('year', Stamps.date) == date.year,
            extract('month', Stamps.date) == date.month,
            extract('day', Stamps.date) == date.day
        ).first() or []
    else:
        return db.query(Stamps).filter(
            Stamps.user_id == user_id,
            extract('year', Stamps.date) == date.year,
            extract('month', Stamps.date) == date.month,
        ).all() or []

def getStampRecord(db: Session, user_id: int, date: datetime) -> StampRecord:
    from sqlalchemy import func
    avg = db.query(func.avg(Stamps.stamp_lev)).filter(
        Stamps.user_id == user_id,
        extract('year', Stamps.date) == date.year,
        extract('month', Stamps.date) == date.month,
    ).scalar() or 0

    return StampRecord(year=date.year,month=date.month,average_of_stamp_lev=round(avg))

def findAllCountStamp(db: Session, user_id: int) -> StampCount:
     total_count = db.query(func.count(Stamps.id)).filter(
        Stamps.user_id == user_id,
     ).scalar() or 0
     return StampCount(total_count_of_stamp=total_count)




