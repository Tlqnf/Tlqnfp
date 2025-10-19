
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import uuid
import json
from pydantic import ValidationError
from starlette import status

from models.user import User
from schemas.user import UserUpdate, FCMTokenUpdate, ProfileDescriptionStatus
from storage.base import BaseStorage

def get_user_profile(user_id: int, db: Session) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

def update_my_profile(
    db: Session,
    current_user: User,
    storage: BaseStorage,
    user_data: str,
    profile_pic_file: Optional[UploadFile]
) -> User:
    try:
        user_update_schema = UserUpdate(**json.loads(user_data))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for user_data")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    for field, value in user_update_schema.dict(exclude_unset=True).items():
        setattr(current_user, field, value)

    if profile_pic_file:
        file_extension = profile_pic_file.filename.split(".")[-1]
        filename = f"profile_pic_{current_user.id}_{uuid.uuid4()}.{file_extension}"
        
        profile_pic_url = storage.save(file=profile_pic_file, filename=filename, folder="profile")
        
        current_user.profile_pic = profile_pic_url
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return current_user

def check_user_exists(user: str, db: Session) -> bool:
    mention_user = db.query(User).filter(User.username == user).first()
    return mention_user is not None

def update_fcm_token(fcm_token_update: FCMTokenUpdate, db: Session, current_user: User) -> User:
    current_user.fcm_token = fcm_token_update.fcm_token
    current_user.fcm_token_updated_at = datetime.now(timezone.utc)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user

def logout(db: Session, current_user: User) -> dict:
    current_user.fcm_token = None
    current_user.fcm_token_updated_at = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return {"message": "FCM token cleared successfully."}

def get_profile_description_status(current_user: User) -> ProfileDescriptionStatus:
    is_null = current_user.profile_description is None
    return ProfileDescriptionStatus(is_null=is_null)

def delete_my_account(db: Session, current_user: User):
    user_to_delete = db.query(User).filter(User.id == current_user.id).first()

    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_to_delete.bookmarked_posts.clear()

    db.delete(user_to_delete)
    db.commit()
