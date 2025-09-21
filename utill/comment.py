from sqlalchemy.orm import Session, selectinload
from typing import List

from models.user import User
from models.community import Comment
from models.notification import Notification,Mention
from schemas.community import CommentResponse # Assuming CommentResponse is needed for return type
from utils.fcm import send_push_notification


def process_mentions_and_notifications(
        db: Session,
        mentions: list[str],
        new_comment: Comment,
        current_user: User
):
    """
    Processes mentions in a comment, creates Mention records, and sends notifications.

    Args:
        db (Session): The database session.
        mentions (list[str]): A list of usernames mentioned in the comment.
        new_comment (Comment): The newly created comment object.
        current_user (User): The user who created the comment.
    """
    if not mentions:
        return

    for mentioned_username in mentions:
        mentioned_user = db.query(User).filter(User.username == mentioned_username).first()
        if not mentioned_user:
            continue

        mention = Mention(comment_id=new_comment.id, user_id=mentioned_user.id)
        db.add(mention)

        notification = Notification(
            user_id=mentioned_user.id,
            comment_id=new_comment.id,
            type="mention",
            message=f"{current_user.username}님이 회원님을 멘션했습니다."
        )
        db.add(notification)

        if hasattr(mentioned_user, 'fcm_token') and mentioned_user.fcm_token:
            send_push_notification(
                db=db,
                user=mentioned_user,
                device_token=mentioned_user.fcm_token,
                message=f"{current_user.username}님이 댓글에서 회원님을 멘션했습니다."
            )

def get_replies(db: Session, parent_comment_id: int) -> List[CommentResponse]:
    """
    Retrieves replies for a given parent comment ID.
    """
    replies = db.query(Comment).options(selectinload(Comment.author)).filter(Comment.parent_id == parent_comment_id).all()
    return [
        CommentResponse(
            id=reply.id,
            user_id=reply.user_id, 
            content=reply.content,
            like_count=reply.like_count,
            post_id=reply.post_id,
            parent_id=reply.parent_id,
            created_at=reply.created_at,
            updated_at=reply.updated_at,
            author=reply.author,
            # Add other fields as necessary from the Comment model
        )
        for reply in replies
    ]
