from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import uuid # For unique filenames
import json # Add this import
from pydantic import ValidationError # Add this import

from database import get_db
from models.user import User
from schemas.user import UserUpdate, UserResponse, FCMTokenUpdate, ProfileDescriptionStatus
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
        profile_pic_url = storage.save(file=profile_pic_file, filename=filename, folder="profile")
        
        # Update the user's profile_pic URL
        current_user.profile_pic = profile_pic_url
    
    db.add(current_user) # Add the modified object to the session
    db.commit()
    db.refresh(current_user) # Refresh to get any database-generated updates (e.g., updated_at)
    
    return current_user

@router.get("/mention/check", response_model=bool)
def check(user: str, db: Session = Depends(get_db)):
    mention_user = db.query(User).filter(User.username == user).first()
    return mention_user is not None

@router.patch("/me/fcm-token", response_model=UserResponse)
def update_fcm_token(
    fcm_token_update: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인한 사용자의 FCM 토큰을 업데이트합니다.
    """
    current_user.fcm_token = fcm_token_update.fcm_token
    current_user.fcm_token_updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/logout", response_model=dict)
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자의 FCM 토큰을 삭제합니다.
    """
    current_user.fcm_token = None
    current_user.fcm_token_updated_at = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "FCM token cleared successfully."}

@router.get("/me/profile-description-status", response_model=ProfileDescriptionStatus)
def get_profile_description_status(current_user: User = Depends(get_current_user)):
    is_null = current_user.profile_description is None
    return ProfileDescriptionStatus(is_null=is_null)

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes the current user's account and anonymizes their data.
    """
    user_to_delete = db.query(User).filter(User.id == current_user.id).first()

    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Anonymize associated data
    for post in user_to_delete.posts:
        post.user_id = None
    for comment in user_to_delete.comments:
        comment.user_id = None
    for report in user_to_delete.reports:
        report.user_id = None
    for route in user_to_delete.routes:
        route.user_id = None
    
    user_to_delete.bookmarked_posts.clear()

    db.delete(user_to_delete)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)