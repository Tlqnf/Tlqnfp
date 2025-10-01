
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session, selectinload, aliased
from typing import List, Optional
import uuid
import json
from pydantic import ValidationError
from sqlalchemy import func
from starlette import status

from models import Post, Comment, User, Image, Report
from schemas.community import PostCreate, PostUpdate, PostResponse, CommentCreate, CommentUpdate, Comment as CommentSchema, PostSearchResponse, PostCreateResponse
from storage.base import BaseStorage
from utill.comment import get_replies, process_mentions_and_notifications

def get_boards(
    db: Session,
    page: int,
    page_size: int
) -> list[PostSearchResponse]:
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
            model.route_id = post.report.route.id
        response.append(model)

    return response

def create_board(
    db: Session,
    current_user: User,
    storage: BaseStorage,
    post_data: str,
    images: Optional[List[UploadFile]],
    map_image: UploadFile
) -> PostCreateResponse:
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
        db.add(new_post)
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

def get_board(post_id: int, db: Session) -> PostResponse:
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

def update_board(
    post_id: int,
    post_update: str,
    db: Session,
    current_user: User,
    map_image: Optional[UploadFile],
    new_images: Optional[List[UploadFile]],
    storage: BaseStorage
) -> PostResponse:
    try:
        post_update_data = PostUpdate.model_validate_json(post_update)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for post_update")

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="수정 권한이 없습니다.")

    for key, value in post_update_data.dict(exclude_unset=True).items():
        setattr(post, key, value)

    if map_image is not None:
        if map_image.filename:
            if post.map_image_url:
                storage.delete(post.map_image_url)
            file_extension = map_image.filename.split(".")[-1]
            filename = f"map_{uuid.uuid4()}.{file_extension}"
            map_image_url = storage.save(file=map_image, filename=filename, folder="board")
            post.map_image_url = map_image_url
        else:
            if post.map_image_url:
                storage.delete(post.map_image_url)
            post.map_image_url = None

    current_images = {img.id: img for img in post.images}
    ids_to_keep = set(post_update_data.images_to_keep_ids) if post_update_data.images_to_keep_ids else set()

    for img_id, img_obj in current_images.items():
        if img_id not in ids_to_keep:
            storage.delete(img_obj.url)
            db.delete(img_obj)

    if new_images:
        for image_file in new_images:
            if image_file.filename:
                file_extension = image_file.filename.split(".")[-1]
                filename = f"{uuid.uuid4()}.{file_extension}"
                image_url = storage.save(file=image_file, filename=filename, folder="board")
                new_image = Image(url=image_url, post_id=post.id)
                db.add(new_image)
                post.images.append(new_image)

    db.commit()
    db.refresh(post)
    post_response = PostResponse.model_validate(post)
    if post.report and post.report.route:
        post_response.route_name = post.report.route.name
    return post_response

def delete_board(post_id: int, db: Session, current_user: User, storage: BaseStorage):
    post = db.query(Post).options(selectinload(Post.images)).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

    for image in post.images:
        storage.delete(image.url)

    if post.map_image_url:
        storage.delete(post.map_image_url)

    db.delete(post)
    db.commit()
    return {"message": "글 삭제 성공"}

def toggle_post_like(post_id: int, db: Session, current_user: User) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if current_user in post.liked_by_users:
        post.liked_by_users.remove(current_user)
        post.like_count -= 1
        action = "unliked"
    else:
        post.liked_by_users.append(current_user)
        post.like_count += 1
        action = "liked"

    db.commit()
    db.refresh(post)

    return {"status": action, "like_count": post.like_count}

def check_post_liked_status(post_id: int, db: Session, current_user: User) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_liked = current_user in post.liked_by_users
    return {"is_liked": is_liked}

def create_comment(post_id: int, comment: CommentCreate, db: Session, current_user: User) -> CommentSchema:
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

    db.commit()
    db.refresh(new_comment)
    return new_comment

def get_all_comment(post_id: int, db: Session) -> list[CommentSchema]:
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

def update_comment(comment_id: int, comment_update: CommentUpdate, db: Session, current_user: User) -> CommentSchema:
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

    db.commit()
    db.refresh(comment)
    return comment

def delete_comment(comment_id: int, db: Session, current_user: User):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")
    db.delete(comment)
    db.commit()
    return {"message": "댓글 삭제 성공"}

def read_replies(comment_id: int, db: Session):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    return get_replies(db, comment_id)

def toggle_comment_like(comment_id: int, db: Session, current_user: User) -> dict:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if current_user in comment.liked_by_users:
        comment.liked_by_users.remove(current_user)
        comment.like_count -= 1
        action = "unliked"
    else:
        comment.liked_by_users.append(current_user)
        comment.like_count += 1
        action = "liked"

    db.commit()
    db.refresh(comment)

    return {"status": action, "like_count": comment.like_count}

def check_comment_liked_status(comment_id: int, db: Session, current_user: User) -> dict:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    is_liked = current_user in comment.liked_by_users
    return {"is_liked": is_liked}

def get_my_bookmarked_posts(
    current_user: User,
    db: Session,
    page: int,
    page_size: int
) -> List[PostSearchResponse]:
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

def get_my_posts(
    current_user: User,
    db: Session,
    page: int,
    page_size: int
) -> List[PostSearchResponse]:
    skip = (page - 1) * page_size

    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    my_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                   .options(selectinload(Post.report).selectinload(Report.route), selectinload(Post.images))
                                   .filter(Post.user_id == current_user.id)
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                   .order_by(Post.created_at.desc()).offset(skip).limit(page_size).all())

    response = []
    for post, count in my_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        if post.report and post.report.route:
            model.route_id = post.report.route.id
            model.route_name = post.report.route.name
        response.append(model)

    return response

def get_my_recent_posts(current_user: User, db: Session) -> List[PostSearchResponse]:
    comment_count_subquery = db.query(
        Comment.post_id,
        func.count(Comment.id).label("comment_count")
    ).group_by(Comment.post_id).subquery()

    my_posts_with_comment_count = (db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
                                   .options(selectinload(Post.report).selectinload(Report.route), selectinload(Post.images))
                                   .filter(Post.user_id == current_user.id)
                                   .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
                                   .order_by(Post.created_at.desc()).limit(4).all())

    response = []
    for post, count in my_posts_with_comment_count:
        model = PostSearchResponse.model_validate(post)
        model.comment_count = count
        if post.report and post.report.route:
            model.route_id = post.report.route.id
            model.route_name = post.report.route.name
        response.append(model)

    return response

def get_my_recent_bookmarked_posts(current_user: User, db: Session) -> List[PostSearchResponse]:
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

def bookmark_post(post_id: int, db: Session, current_user: User):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    if post in current_user.bookmarked_posts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Post already bookmarked")

    current_user.bookmarked_posts.append(post)
    db.commit()

def unbookmark_post(post_id: int, db: Session, current_user: User):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post not in current_user.bookmarked_posts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Post not bookmarked")

    current_user.bookmarked_posts.remove(post)
    db.commit()

def is_bookmarked(post_id: int, current_user: User, db: Session) -> dict:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    is_bookmarked = post in current_user.bookmarked_posts
    return {"is_bookmarked": is_bookmarked}
