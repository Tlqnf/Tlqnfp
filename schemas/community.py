from pydantic import BaseModel, field_validator, computed_field # Add computed_field
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
    user_id: Optional[int] = None
    report: Optional[ReportWithRouteResponse] = None
    created_at: datetime
    images: List[Image] = []
    hash_tag: List[str]
    public: bool
    speed: Optional[float] = None
    distance: Optional[float] = None
    time: Optional[float] = None
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