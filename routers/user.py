
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile, Response
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models.user import User
from schemas.user import UserResponse, FCMTokenUpdate, ProfileDescriptionStatus
from utils.auth import get_current_user
from storage.base import BaseStorage
from dependencies import get_storage_manager
from services import user as user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자의 프로필 정보를 조회합니다."""
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """ID로 특정 사용자의 프로필 정보를 조회합니다."""
    return user_service.get_user_profile(user_id, db)

@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: BaseStorage = Depends(get_storage_manager),
    user_data: str = Form(...),
    profile_pic_file: Optional[UploadFile] = File(None)
):
    """현재 로그인한 사용자의 프로필 정보를 업데이트합니다."""
    return user_service.update_my_profile(db, current_user, storage, user_data, profile_pic_file)

@router.get("/mention/check", response_model=bool)
def check(user: str, db: Session = Depends(get_db)):
    return user_service.check_user_exists(user, db)

@router.patch("/me/fcm-token", response_model=UserResponse)
def update_fcm_token(
    fcm_token_update: FCMTokenUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인한 사용자의 FCM 토큰을 업데이트합니다.
    """
    return user_service.update_fcm_token(fcm_token_update, db, current_user)

@router.post("/me/logout", response_model=dict)
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자의 FCM 토큰을 삭제합니다.
    """
    return user_service.logout(db, current_user)

@router.get("/me/profile-description-status", response_model=ProfileDescriptionStatus)
def get_profile_description_status(current_user: User = Depends(get_current_user)):
    return user_service.get_profile_description_status(current_user)

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deletes the current user's account and anonymizes their data.
    """
    user_service.delete_my_account(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
