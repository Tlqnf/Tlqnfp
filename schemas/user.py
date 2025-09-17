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