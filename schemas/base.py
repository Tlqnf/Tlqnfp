from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from zoneinfo import ZoneInfo

# Define the timezone for Asia/Seoul
SEOUL_TZ = ZoneInfo("Asia/Seoul")

# Custom JSON encoder for datetime objects
def convert_datetime_to_korea_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        # Assume UTC if timezone is not set (common for DB retrieved naive datetimes)
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(SEOUL_TZ).isoformat()

class RouteBase(BaseModel):
    name: Optional[str] = None

class Route(RouteBase):
    id: int
    created_at: datetime
    points_json: Optional[List[Dict[str, Any]]] = []
    start_point: Optional[Dict[str, Any]] = None
    end_point: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}
