from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo # Add this import

from schemas.route import Route, RoutePointsResponse, RouteWithReportsResponse
from schemas.report import AllReportResponse, ReportListResponse

# Define the timezone for Asia/Seoul
SEOUL_TZ = ZoneInfo("Asia/Seoul")

# Custom JSON encoder for datetime objects
def convert_datetime_to_korea_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        # Assume UTC if timezone is not set (common for DB retrieved naive datetimes)
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(SEOUL_TZ).isoformat()

# ---------- Image ----------
class Image(BaseModel):
    id: int
    url: str

    class Config:
        from_attributes = True

# ---------- Post ----------
class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    like_count: int
    read_count: int
    user_id: Optional[int] = None
    route_id: Optional[int] = None
    route: Optional[RouteWithReportsResponse] = None
    created_at: datetime
    images: List[Image] = []

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class PostCreate(BaseModel):
    title: str
    content: str
    route_id: Optional[int] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# ---------- Comment (New Recursive Structure) ----------

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

class CommentUpdate(BaseModel):
    content: str

class Comment(BaseModel):
    id: int
    content: str
    user_id: int
    post_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    children: List["Comment"] = []

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

# ---------- AllPostResponse (Updated to use new Comment schema) ----------

class AllPostResponse(BaseModel):
    id: int
    title: str
    content: str
    like_count: int
    read_count: int
    user_id: int
    route_id: Optional[int] = None
    route: Optional[Route] = None
    reports: List[AllReportResponse] = []
    comments: List[Comment] = []
    images: List[Image] = []

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this
