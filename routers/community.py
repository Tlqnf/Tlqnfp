from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session, selectinload, aliased
from typing import List, Optional
import uuid
import json # Add this import
from pydantic import ValidationError, BaseModel  # Add this import
from sqlalchemy import func
from starlette import status

from models import Post, Comment, Route, User, Image, Report, Mention, Notification
from schemas.community import (
    PostCreate, PostUpdate, PostResponse, CommentResponse,
    CommentCreate, CommentUpdate, Comment as CommentSchema, AllPostResponse,
    PostSummaryResponse, PostCreateResponse, PostSearchResponse # Add PostSummaryResponse
)
from database import get_db
from utils.auth import get_current_user
from storage.base import BaseStorage
from dependencies import get_storage_manager

from utill.comment import get_replies
from utill.comment import process_mentions_and_notifications

router = APIRouter(prefix="/post", tags=["community"])


# ---------------------- 게시글 ----------------------
@router.get("", response_model=list[PostSearchResponse])
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

    posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                .options(
                                    selectinload(Post.images),
                                    selectinload(Post.report).selectinload(Report.route),
                                    selectinload(Post.author)
                                )
                                .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                .filter(Post.public == True).order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    response = []
    for post, count in posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        if post.report and post.report.route:
            model.route_name = post.report.route.name
        response.append(model)

    return response


@router.post("", response_model=PostCreateResponse)
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

    post_response = PostCreateResponse.model_validate(new_post)
    if new_post.report and new_post.report.route:
        post_response.route_name = new_post.report.route.name
    return post_response


@router.get("/{post_id}", response_model=PostResponse)
def get_board(
    post_id: int,
    db: Session = Depends(get_db)
):
    """특정 ID의 게시글 상세 정보를 조회합니다."""
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    result = (
        db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
        .options(
            selectinload(Post.images),
            selectinload(Post.report).selectinload(Report.route),
            selectinload(Post.author)
        )
        .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
        .filter(Post.id == post_id)
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    post, count = result
    post_response = PostResponse.model_validate(post, update={'comment_count': count})
    if post.report and post.report.route:
        post_response.route_name = post.report.route.name
    return post_response


@router.patch("/{post_id}", response_model=PostResponse)
def update_board(
    post_id: int,
    post_update: PostUpdate, # Use Depends() for Pydantic model in Form data
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    map_image: Optional[UploadFile] = File(None),
    new_images: Optional[List[UploadFile]] = File(None),
    storage: BaseStorage = Depends(get_storage_manager),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")

    # Update post fields
    for key, value in post_update.dict(exclude_unset=True).items():
        setattr(post, key, value)

    # Handle map image update
    # If map_image is provided (even if it's None to clear it)
    if map_image is not None:
        # If a new file is uploaded
        if map_image.filename:
            # Delete old map image if it exists
            if post.map_image_url:
                storage.delete(post.map_image_url)
            file_extension = map_image.filename.split(".")[-1]
            filename = f"map_{uuid.uuid4()}.{file_extension}"
            map_image_url = storage.save(file=map_image, filename=filename, folder="board")
            post.map_image_url = map_image_url
        else: # If map_image is explicitly None (no filename), it means client wants to remove it
            if post.map_image_url:
                storage.delete(post.map_image_url)
            post.map_image_url = None

    # Handle general images
    current_images = {img.id: img for img in post.images}
    ids_to_keep = set(post_update.images_to_keep_ids) if post_update.images_to_keep_ids else set()

    # Delete images not in ids_to_keep
    for img_id, img_obj in current_images.items():
        if img_id not in ids_to_keep:
            storage.delete(img_obj.url) # Delete from storage
            db.delete(img_obj) # Delete from database
            # The relationship will be updated automatically by SQLAlchemy's cascade or refresh

    # Add new images
    if new_images:
        for image_file in new_images:
            if image_file.filename:
                file_extension = image_file.filename.split(".")[-1]
                filename = f"{uuid.uuid4()}.{file_extension}"
                image_url = storage.save(file=image_file, filename=filename, folder="board")
                new_image = Image(url=image_url, post_id=post.id)
                db.add(new_image)
                post.images.append(new_image) # Add to relationship

    db.commit()
    db.refresh(post)
    post_response = PostResponse.model_validate(post)
    if post.report and post.report.route:
        post_response.route_name = post.report.route.name
    return post_response


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


@router.post("/{post_id}/like", response_model=dict)
def toggle_post_like(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Toggles the current user's like status for a specific post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if current_user in post.liked_by_users:
        # User has already liked the post, so unlike it
        post.liked_by_users.remove(current_user)
        post.like_count -= 1
        action = "unliked"
    else:
        # User has not liked the post, so like it
        post.liked_by_users.append(current_user)
        post.like_count += 1
        action = "liked"

    db.commit()
    db.refresh(post)

    return {"status": action, "like_count": post.like_count}


@router.get("/{post_id}/is_liked", response_model=dict)
def check_post_liked_status(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Checks if the current user has liked a specific post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_liked = current_user in post.liked_by_users
    return {"is_liked": is_liked}

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
    ChildComment = aliased(Comment)

    comments_with_count = (
        db.query(
            Comment,
            func.count(ChildComment.id).label("comment_count")
        )
        .outerjoin(ChildComment, ChildComment.parent_id == Comment.id)
        .filter(Comment.post_id == post_id, Comment.parent_id.is_(None))
        .group_by(Comment.id)
        .all()
    )

    if not comments_with_count:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

    result = []
    for comment, count in comments_with_count:
        # Manually construct the CommentSchema to ensure correct field mapping
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


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    db.delete(comment)
    db.commit()
    return {"message": "댓글 삭제 성공"}



@router.get("/comments/{comment_id}/replies", response_model=List[CommentResponse])
def read_replies(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return get_replies(db, comment_id)







# -------------------------------
# Delete (댓글 / 대댓글 삭제)
# -------------------------------


@router.post("/comments/{comment_id}/like", response_model=dict)
def toggle_comment_like(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Toggles the current user's like status for a specific comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if current_user in comment.liked_by_users:
        # User has already liked the comment, so unlike it
        comment.liked_by_users.remove(current_user)
        comment.like_count -= 1
        action = "unliked"
    else:
        # User has not liked the comment, so like it
        comment.liked_by_users.append(current_user)
        comment.like_count += 1
        action = "liked"

    db.commit()
    db.refresh(comment)

    return {"status": action, "like_count": comment.like_count}


@router.get("/comments/{comment_id}/is_liked", response_model=dict)
def check_comment_liked_status(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Checks if the current user has liked a specific comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    is_liked = current_user in comment.liked_by_users
    return {"is_liked": is_liked}


@router.get("/me/bookmarked", response_model=List[PostSearchResponse])
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

    bookmarked_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                           .options(selectinload(Post.report), selectinload(Post.images))
                                           .join(User.bookmarked_posts).filter(User.id == current_user.id)
                                           .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                           .order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    response = []
    for post, count in bookmarked_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        response.append(model)

    return response


@router.get("/me/posts", response_model=List[PostSearchResponse])
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

    my_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                   .options(selectinload(Post.report), selectinload(Post.images))
                                   .filter(Post.user_id == current_user.id)
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                   .order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    response = []
    for post, count in my_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        response.append(model)

    return response


@router.get("/me/posts/recent", response_model=List[PostSearchResponse])
def get_my_recent_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 작성한 최근 4개의 게시글을 반환합니다."""
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    my_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                   .options(selectinload(Post.report), selectinload(Post.images))
                                   .filter(Post.user_id == current_user.id)
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                   .order_by(Post.created_at.desc()).limit(4).all())

    response = []
    for post, count in my_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        response.append(model)

    return response


@router.get("/me/bookmarked/recent", response_model=List[PostSearchResponse])
def get_my_recent_bookmarked_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 사용자가 북마크한 최근 4개의 게시글을 반환합니다."""
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    bookmarked_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                           .options(selectinload(Post.report), selectinload(Post.images))
                                           .join(User.bookmarked_posts).filter(User.id == current_user.id)
                                           .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                           .order_by(Post.created_at.desc()).limit(4).all())

    response = []
    for post, count in bookmarked_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        response.append(model)

    return response


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


class IsBookmarked(BaseModel):
    is_bookmarked: bool

@router.get("/{post_id}/is-bookmarked", status_code=status.HTTP_200_OK, response_model=IsBookmarked)
def is_bookmarked(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Checks if the current user has bookmarked a specific post."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_bookmarked = post in current_user.bookmarked_posts
    return {"is_bookmarked": is_bookmarked}