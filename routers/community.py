from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
import uuid
import json # Add this import
from pydantic import ValidationError # Add this import

from models import Post, Comment, Route, User, Image
from schemas.community import (
    PostCreate, PostUpdate, PostResponse,
    CommentCreate, CommentUpdate, Comment as CommentSchema, AllPostResponse
)
from database import get_db
from utils.auth import get_current_user
from storage.base import BaseStorage
from dependencies import get_storage_manager

router = APIRouter(prefix="/post", tags=["community"])


# ---------------------- 게시글 ----------------------
@router.get("", response_model=list[PostResponse])
def get_boards(db: Session = Depends(get_db)):
    posts = db.query(Post).options(
        selectinload(Post.images),
        selectinload(Post.route).options(selectinload(Route.reports))
    ).all()
    return posts

@router.get("/{post_id}", response_model=AllPostResponse)
def get_board(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).options(
        selectinload(Post.images),
        selectinload(Post.comments),
        selectinload(Post.route).selectinload(Route.reports)
    ).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    return post


@router.post("", response_model=PostResponse)
def create_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: BaseStorage = Depends(get_storage_manager),
    post_data: str = Form(...),
    images: List[UploadFile] = File(...)
):
    # Parse post_data as JSON and validate with PostCreate schema
    try:
        post_data_dict = json.loads(post_data)
        post_create_schema = PostCreate(**post_data_dict)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for post_data")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    if post_create_schema.route_id:
        route = db.query(Route).filter(Route.id == post_create_schema.route_id).first()
        if not route:
            raise HTTPException(status_code=404, detail="연결하려는 경로를 찾을 수 없습니다.")

    # 1. Create the Post object
    new_post = Post(
        title=post_create_schema.title,
        content=post_create_schema.content,
        route_id=post_create_schema.route_id,
        user_id=current_user.id
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    # 2. Save images and create Image records
    if images:
        for image in images:
            # Generate a unique filename
            file_extension = image.filename.split(".")[-1]
            filename = f"{uuid.uuid4()}.{file_extension}"
            
            # Save the file using the storage manager
            image_url = storage.save(file=image, filename=filename)
            
            # Create the Image record
            new_image = Image(url=image_url, post_id=new_post.id)
            db.add(new_image)
        
        db.commit()
        db.refresh(new_post) # Refresh again to load the new images relationship

    return new_post


@router.patch("/{post_id}", response_model=PostResponse)
def update_board(post_id: int, post_update: PostUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")
    for key, value in post_update.dict(exclude_unset=True).items():
        setattr(post, key, value)
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


@router.post("/{post_id}/like")
def recommend_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    post.like_count += 1
    db.commit()
    return {"message": "좋아요 증가", "like_count": post.like_count}


@router.post("/{post_id}/read")
def read_board(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    post.read_count += 1
    db.commit()
    return {"message": "조회수 증가", "read_count": post.read_count}


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
    return new_comment


@router.get("/comments/{comment_id}", response_model=CommentSchema)
def get_comment(comment_id: int, db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")
    return comment


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
