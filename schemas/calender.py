from datetime import datetime
from calendar import monthrange

from pydantic import BaseModel, computed_field


class CalenderStampData(BaseModel):
    stamp_lev: int
    date: datetime

class StampRecord(BaseModel):
    year: int
    month: int
    average_of_stamp_lev: int

    @computed_field
    @property
    def days_of_month(self: datetime) -> int:
        return monthrange(self.year, self.month)[1]

    class Config:
        from_attributes = True


class StampCount(BaseModel):
    total_count_of_stamp: int