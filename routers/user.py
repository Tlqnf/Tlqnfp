from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
import uuid # For unique filenames
import json # Add this import
from pydantic import ValidationError # Add this import

from database import get_db
from models.user import User
from schemas.user import UserUpdate, UserResponse
from utils.auth import get_current_user
from storage.base import BaseStorage # Import BaseStorage
from dependencies import get_storage_manager # Import get_storage_manager

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자의 프로필 정보를 조회합니다."""
    return current_user

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: BaseStorage = Depends(get_storage_manager),
    user_data: str = Form(...),
    profile_pic_file: Optional[UploadFile] = File(None)
):
    """현재 로그인한 사용자의 프로필 정보를 업데이트합니다."""
    # Parse user_data as JSON and validate with UserUpdate schema
    try:
        user_update_schema = UserUpdate(**json.loads(user_data))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for user_data")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    # Update user fields from the UserUpdate schema
    for field, value in user_update_schema.dict(exclude_unset=True).items():
        setattr(current_user, field, value)

    # Handle profile picture upload
    if profile_pic_file:
        # Generate a unique filename for the profile picture
        file_extension = profile_pic_file.filename.split(".")[-1]
        filename = f"profile_pic_{current_user.id}_{uuid.uuid4()}.{file_extension}"
        
        # Save the file using the storage manager
        profile_pic_url = storage.save(file=profile_pic_file, filename=filename)
        
        # Update the user's profile_pic URL
        current_user.profile_pic = profile_pic_url
    
    db.add(current_user) # Add the modified object to the session
    db.commit()
    db.refresh(current_user) # Refresh to get any database-generated updates (e.g., updated_at)
    
    return current_user