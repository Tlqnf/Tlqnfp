
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.notice import Notice
from schemas.notice import NoticeCreate, NoticeUpdate
from models.user import User

def get_notices(db: Session, skip: int = 0, limit: int = 100) -> List[Notice]:
    return db.query(Notice).offset(skip).limit(limit).all()

def get_notice(db: Session, notice_id: int) -> Notice:
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")
    return notice

def create_notice(db: Session, notice: NoticeCreate, current_user: User) -> Notice:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create a notice")
    
    new_notice = Notice(**notice.dict())
    db.add(new_notice)
    db.commit()
    db.refresh(new_notice)
    return new_notice

def update_notice(db: Session, notice_id: int, notice: NoticeUpdate, current_user: User) -> Notice:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update a notice")

    db_notice = get_notice(db, notice_id)
    
    for key, value in notice.dict(exclude_unset=True).items():
        setattr(db_notice, key, value)
        
    db.commit()
    db.refresh(db_notice)
    return db_notice

def delete_notice(db: Session, notice_id: int, current_user: User):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete a notice")

    db_notice = get_notice(db, notice_id)
    
    db.delete(db_notice)
    db.commit()
    return {"message": "Notice deleted successfully"}
