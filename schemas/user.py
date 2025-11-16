from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    profile_description: Optional[str] = None
    profile_pic: Optional[str] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    profile_description: Optional[str] = None
    profile_pic: Optional[str] = None # Re-add this

# New schema for OAuth callbacks
class TokenUserResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class FCMTokenUpdate(BaseModel):
    fcm_token: Optional[str] = None

class ProfileDescriptionStatus(BaseModel):
    is_null: bool


from datetime import datetime

class SubscriptionStatusResponse(BaseModel):
    is_subscribed: bool
    subscription_expiry_date: Optional[datetime] = None

    class Config:
        from_attributes = True