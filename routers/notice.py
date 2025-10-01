
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas.notice import Notice, NoticeCreate, NoticeUpdate
from services import notice as notice_service
from utils.auth import get_current_user
from models.user import User

router = APIRouter(
    prefix="/notices",
    tags=["notices"]
)

@router.get("", response_model=List[Notice])
def get_notices(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    return notice_service.get_notices(db, skip, limit)

@router.get("/{notice_id}", response_model=Notice)
def get_notice(notice_id: int, db: Session = Depends(get_db)):
    return notice_service.get_notice(db, notice_id)

@router.post("", response_model=Notice, status_code=status.HTTP_201_CREATED)
def create_notice(notice: NoticeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return notice_service.create_notice(db, notice, current_user)

@router.patch("/{notice_id}", response_model=Notice)
def update_notice(notice_id: int, notice: NoticeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return notice_service.update_notice(db, notice_id, notice, current_user)

@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(notice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return notice_service.delete_notice(db, notice_id, current_user)
