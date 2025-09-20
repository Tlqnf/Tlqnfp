from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
import uuid
import json # Add this import
from pydantic import ValidationError # Add this import
from sqlalchemy import func
from starlette import status

from models import Post, Comment, Route, User, Image, Report, Mention, Notification
from schemas.community import (
    PostCreate, PostUpdate, PostResponse, CommentResponse,
    CommentCreate, CommentUpdate, Comment as CommentSchema, AllPostResponse,
    PostSummaryResponse # Add PostSummaryResponse
)
from database import get_db
from utils.auth import get_current_user
from storage.base import BaseStorage
from dependencies import get_storage_manager

from utill.comment import get_replies
from utill.comment import process_mentions_and_notifications

router = APIRouter(prefix="/post", tags=["community"])


# ---------------------- 게시글 ----------------------
@router.get("", response_model=list[PostResponse])
def get_boards(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    skip = (page - 1) * page_size

    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    posts_with_comment_count = (db.query(Post).options(
        selectinload(Post.images),
        selectinload(Post.report).selectinload(Report.route),
        selectinload(Post.author)
    ).outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                .add_columns(func.coalesce(comment_count_subquery.c.comment_count, 0).label("comment_count"))
                                .filter(Post.public == True).order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    return [
        PostResponse.model_validate(post, update={'comment_count': count})
        for post, count in posts_with_comment_count
    ]


@router.post("", response_model=PostResponse)
def create_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: BaseStorage = Depends(get_storage_manager),
    post_data: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    map_image: UploadFile = File(...),
):
    try:
        post_data_dict = json.loads(post_data)
        post_create_schema = PostCreate(**post_data_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for post_data")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    if post_create_schema.report_id:
        report = db.query(Report).filter(Report.id == post_create_schema.report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="연결하려는 리포트를 찾을 수 없습니다.")

    new_post = Post(
        title=post_create_schema.title,
        content=post_create_schema.content,
        report_id=post_create_schema.report_id,
        user_id=current_user.id,
        hash_tag=post_create_schema.hash_tag,
        public=post_create_schema.public,
        speed=post_create_schema.speed,
        distance=post_create_schema.distance,
        time=post_create_schema.time,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    if map_image and map_image.filename:
        file_extension = map_image.filename.split(".")[-1]
        filename = f"map_{uuid.uuid4()}.{file_extension}"
        map_image_url = storage.save(file=map_image, filename=filename, folder="board")
        new_post.map_image_url = map_image_url
        db.add(new_post) # Add new_post to session to track changes
        db.commit()
        db.refresh(new_post)

    if images:
        for image in images:
            file_extension = image.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{file_extension}"
            image_url = storage.save(file=image, filename=filename, folder="board")
            new_image = Image(url=image_url, post_id=new_post.id)
            db.add(new_image)
        db.commit()
        db.refresh(new_post)

    return new_post


@router.patch("/{post_id}", response_model=PostResponse)
def update_board(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    map_image: Optional[UploadFile] = File(None),
    storage: BaseStorage = Depends(get_storage_manager),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
    for key, value in post_update.dict(exclude_unset=True).items():
        setattr(post, key, value)

    if map_image and map_image.filename:
        file_extension = map_image.filename.split(".")[-1]
        filename = f"map_{uuid.uuid4()}.{file_extension}"
        map_image_url = storage.save(file=map_image, filename=filename, folder="board")
        post.map_image_url = map_image_url

    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}")
def delete_board(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    db.delete(post)
    db.commit()
    return {"message": "글 삭제 성공"}


@router.post("/{post_id}/post-like")
def recommend_post(post_id: int, db: Session = Depends(get_db)):
    print(post_id)
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    post.like_count += 1
    db.commit()
    return {"message": "좋아요 증가", "like_count": post.like_count}

@router.post("/{post_id}/post-unlike")
def recommend_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    post.like_count -= 1
    db.commit()
    return {"message": "좋아요 감소", "like_count": post.like_count}

# ---------------------- 댓글 ----------------------
@router.post("/{post_id}/comments", response_model=CommentSchema)
def create_comment(post_id: int, comment: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    if comment.parent_id:
        parent_comment = db.query(Comment).filter(Comment.id == comment.parent_id).first()
        if not parent_comment:
            raise HTTPException(status_code=404, detail="부모 댓글을 찾을 수 없습니다.")
        if parent_comment.post_id != post_id:
            raise HTTPException(status_code=400, detail="부모 댓글이 다른 게시글에 속해 있습니다.")

    new_comment = Comment(
        content=comment.content,
        post_id=post_id,
        user_id=current_user.id,
        parent_id=comment.parent_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    process_mentions_and_notifications(
        db=db,
        mentions=comment.mentions,
        new_comment=new_comment,
        current_user=current_user
    )

    db.commit()  # Commit all mentions and notifications
    db.refresh(new_comment)  # Refresh again after adding mentions/notifications
    return new_comment


@router.get("/{post_id}/comments", response_model=list[CommentSchema])
def get_all_comment(post_id: int, db: Session = Depends(get_db)):
    # 댓글 + 대댓글 개수 계산
    comments = (
        db.query(
            Comment,
            func.count(Comment.children).label("comment_count")  # children 관계 기준 카운트
        )
        .filter(Comment.post_id == post_id, Comment.parent_id == None)  # 최상위 댓글만
        .outerjoin(Comment.children)
        .group_by(Comment.id)
        .all()
    )

    if not comments:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    # 반환 형식 맞추기
    result = []
    for comment, count in comments:
        result.append(
            CommentSchema(
                id=comment.id,
                content=comment.content,
                user_id=comment.user_id,
                post_id=comment.post_id,
                like_count=comment.like_count if hasattr(comment, "like_count") else 0,
                comment_count=count
            )
        )

    return result


@router.patch("/comments/{comment_id}", response_model=CommentSchema)
def update_comment(comment_id: int, comment_update: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
    comment.content = comment_update.content
    db.commit()
    db.refresh(comment)

    process_mentions_and_notifications(
        db=db,
        mentions=comment.mentions,
        new_comment=comment,
        current_user=current_user
    )

    db.commit()  # Commit all mentions and notifications
    db.refresh(comment)  # Refresh again after adding mentions/notifications
    return comment


@router.delete("/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    db.delete(comment)
    db.commit()
    return {"message": "댓글 삭제 성공"}


#대댓글

@router.get("/comments/{comment_id}", response_model=List[CommentResponse])
def read_replies(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return get_replies(db, comment_id)






# -------------------------------
# Update (댓글 / 대댓글 수정)
# -------------------------------
@router.put("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, comment_update: CommentUpdate, db: Session = Depends(get_db)):
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db_comment.content = comment_update.content
    db.commit()
    db.refresh(db_comment)
    return db_comment


# -------------------------------
# Delete (댓글 / 대댓글 삭제)
# -------------------------------
@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db.delete(db_comment)
    db.commit()
    return {"detail": "Comment deleted"}

#댓글 좋아요
@router.post("/{comment_id}/comment-like")
def recommend_post(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    comment.like_count += 1
    db.commit()
    return {"message": "좋아요 감소", "like_count": comment.like_count}

#댓글 좋아요 취소
@router.post("/{comment_id}/comment-unlike")
def recommend_post(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    comment.like_count -= 1
    db.commit()
    return {"message": "좋아요 감소", "like_count": comment.like_count}


@router.get("/me/bookmarked", response_model=List[PostSummaryResponse])
def get_my_bookmarked_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """현재 사용자가 북마크한 모든 게시글의 목록을 반환합니다."""
    skip = (page - 1) * page_size

    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    bookmarked_posts_with_comment_count = (((((db.query(Post)
                                           .options(selectinload(Post.report), selectinload(Post.images)))
                                           .join(User.bookmarked_posts).filter(User.id == current_user.id))
                                           .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id))
                                           .add_columns(func.coalesce(comment_count_subquery.c.comment_count, 0).label("comment_count")))
                                           .order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    return [
        PostSummaryResponse.model_validate(post, update={'comment_count': count})
        for post, count in bookmarked_posts_with_comment_count
    ]


@router.get("/me/posts", response_model=List[PostSummaryResponse])
def get_my_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    """현재 사용자가 작성한 모든 게시글의 목록을 반환합니다."""
    skip = (page - 1) * page_size

    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    my_posts_with_comment_count = (((((db.query(Post)
                                   .options(selectinload(Post.report), selectinload(Post.images)))
                                   .filter(Post.user_id == current_user.id))
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id))
                                   .add_columns(func.coalesce(comment_count_subquery.c.comment_count, 0).label("comment_count")))
                                   .order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    return [
        PostSummaryResponse.model_validate(post, update={'comment_count': count})
        for post, count in my_posts_with_comment_count
    ]


@router.get("/me/posts/recent", response_model=List[PostSummaryResponse])
def get_my_recent_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 작성한 최근 4개의 게시글을 반환합니다."""
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    my_posts_with_comment_count = (((((db.query(Post)
                                   .options(selectinload(Post.report), selectinload(Post.images)))
                                   .filter(Post.user_id == current_user.id))
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id))
                                   .add_columns(func.coalesce(comment_count_subquery.c.comment_count, 0).label("comment_count")))
                                   .order_by(Post.created_at.desc()).limit(4).all())

    return [
        PostSummaryResponse.model_validate(post, update={'comment_count': count})
        for post, count in my_posts_with_comment_count
    ]


@router.get("/me/bookmarked/recent", response_model=List[PostSummaryResponse])
def get_my_recent_bookmarked_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 북마크한 최근 4개의 게시글을 반환합니다."""
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    bookmarked_posts_with_comment_count = (((((db.query(Post)
                                           .options(selectinload(Post.report), selectinload(Post.images)))
                                           .join(User.bookmarked_posts).filter(User.id == current_user.id))
                                           .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id))
                                           .add_columns(func.coalesce(comment_count_subquery.c.comment_count, 0).label("comment_count")))
                                           .order_by(Post.created_at.desc()).limit(4).all())

    return [
        PostSummaryResponse.model_validate(post, update={'comment_count': count})
        for post, count in bookmarked_posts_with_comment_count
    ]


@router.post("/{post_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def bookmark_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """특정 게시글을 현재 사용자의 북마크에 추가합니다."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    if post in current_user.bookmarked_posts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Post already bookmarked")

    current_user.bookmarked_posts.append(post)
    db.commit()

@router.delete("/{post_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def unbookmark_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """특정 게시글을 현재 사용자의 북마크에서 제거합니다."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post not in current_user.bookmarked_posts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Post not bookmarked")

    current_user.bookmarked_posts.remove(post)
    db.commit()
