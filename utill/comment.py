from sqlalchemy.orm import Session, selectinload

from models import Comment

def get_replies(db: Session, comment_id: int):
    """
    특정 댓글(comment_id)의 직접적인 대댓글(1단계)만 반환
    """
    return db.query(Comment).options(selectinload(Comment.author)).filter(
       Comment.parent_id == comment_id
    ).order_by(Comment.created_at).all()
