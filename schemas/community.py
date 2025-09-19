from pydantic import BaseModel, Field, field_validator, computed_field # Add computed_field, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo

from schemas.base import Route, convert_datetime_to_korea_time
from schemas.report import ReportWithRouteResponse
from schemas.user import UserResponse # Import UserResponse

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
    comment_count: int = 0
    user_id: Optional[int] = None
    report: Optional[ReportWithRouteResponse] = None
    created_at: datetime
    images: List[Image] = []
    hash_tag: List[str]
    public: bool
    speed: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None
    map_image_url: Optional[str] = None
    author: Optional[UserResponse] = None # Add author relationship

    @computed_field
    @property
    def username(self) -> Optional[str]:
        return self.author.username if self.author else None

    @computed_field
    @property
    def profile_pic(self) -> Optional[str]:
        return self.author.profile_pic if self.author else None

    @field_validator('hash_tag', mode='before')
    @classmethod
    def hashtags_to_empty_list(cls, v):
        if v is None:
            return []
        return v

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}

class PostSummaryResponse(BaseModel):
    id: int
    title: str
    distance: Optional[float] = None
    created_at: datetime # Original datetime for internal use
    report: Optional[ReportWithRouteResponse] = Field(None, exclude=True) # Exclude from output

    @computed_field
    @property
    def time_hour(self) -> Optional[int]:
        if self.report and self.report.health_time is not None:
            total_seconds = self.report.health_time
            return total_seconds // 3600 # Convert seconds to hours
        return None

    @computed_field
    @property
    def time_minute(self) -> Optional[int]:
        if self.report and self.report.health_time is not None:
            total_seconds = self.report.health_time
            return (total_seconds % 3600) // 60 # Remaining seconds converted to minutes
        return None

    @computed_field
    @property
    def created_at_korea(self) -> Optional[str]:
        if self.created_at:
            # Ensure created_at is timezone-aware, assuming it's stored in UTC if naive
            if self.created_at.tzinfo is None:
                utc_dt = self.created_at.replace(tzinfo=ZoneInfo("UTC"))
            else:
                utc_dt = self.created_at.astimezone(ZoneInfo("UTC"))
            return convert_datetime_to_korea_time(utc_dt)
        return None

    comment_count: int = 0 # Add comment_count
    map_image_url: Optional[str] = None

    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    title: str
    content: str
    report_id: Optional[int] = None
    hash_tag: List[str]
    public: bool
    speed: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None

    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

# ---------- Comment (New Recursive Structure) ----------

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None
    mentions: List[str] = []

class CommentUpdate(BaseModel):
    content: str
    mentions: List[str] = []

class Comment(BaseModel):
    id: int
    content: str
    user_id: int
    post_id: int
    like_count: int = 0
    comment_count: int = 0

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}

# ---------- AllPostResponse (Updated to use new Comment schema) ----------

class AllPostResponse(BaseModel):
    id: int
    title: str
    content: str
    like_count: int
    read_count: int
    user_id: int
    report_id: Optional[int] = None # Changed from route_id
    report: Optional[ReportWithRouteResponse] = None # Changed from route
    comments_amount: int
    images: List[Image] = []
    speed: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}

class CommentResponse(BaseModel):
    id: int
    user_id: int
    content: str
    post_id: Optional[int]
    parent_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    author: Optional[UserResponse] = None

    @computed_field
    @property
    def username(self) -> Optional[str]:
        return self.author.username if self.author else None

    @computed_field
    @property
    def profile_pic(self) -> Optional[str]:
        return self.author.profile_pic if self.author else None

    class Config:
        from_attributes = True