from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo # Add this import

# Define the timezone for Asia/Seoul
SEOUL_TZ = ZoneInfo("Asia/Seoul")

# Custom JSON encoder for datetime objects
def convert_datetime_to_korea_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        # Assume UTC if timezone is not set (common for DB retrieved naive datetimes)
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(SEOUL_TZ).isoformat()

class ReportResponse(BaseModel):
    id: int
    health_time: int
    average_speed: float
    kcal: int
    cumulative_high: int
    increase_slope: float
    created_at: datetime
    route_id: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class AllReportResponse(BaseModel):
    id: int
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: int
    kcal: int
    average_speed: float
    highest_speed: float
    average_face: float
    highest_face: float
    cumulative_high: int
    highest_high: int
    lowest_high: int
    increase_slope: float
    decrease_slope: float
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class ReportListResponse(BaseModel):
    distance: int
    average_speed: float
    health_time: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this
