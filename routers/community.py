
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from starlette import status

from models import User
from schemas.community import (
    PostUpdate, PostResponse, CommentResponse,
    CommentCreate, CommentUpdate, Comment as CommentSchema, PostSearchResponse, PostCreateResponse
)
from database import get_db
from utils.auth import get_current_user
from storage.base import BaseStorage
from dependencies import get_storage_manager
from services import community as community_service
from pydantic import BaseModel

router = APIRouter(prefix="/post", tags=["community"])


# ---------------------- 게시글 ----------------------
@router.get("", response_model=list[PostSearchResponse])
def get_boards(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    return community_service.get_boards(db, page, page_size)


@router.post("", response_model=PostCreateResponse)
def create_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: BaseStorage = Depends(get_storage_manager),
    post_data: str = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    map_image: UploadFile = File(...),
):
    return community_service.create_board(db, current_user, storage, post_data, images, map_image)


@router.get("/{post_id}", response_model=PostResponse)
def get_board(
    post_id: int,
    db: Session = Depends(get_db)
):
    return community_service.get_board(post_id, db)


@router.patch("/{post_id}", response_model=PostResponse)
def update_board(
    post_id: int,
    post_update: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    map_image: Optional[UploadFile] = File(None),
    new_images: Optional[List[UploadFile]] = File(None),
    storage: BaseStorage = Depends(get_storage_manager),
):
    return community_service.update_board(post_id, post_update, db, current_user, map_image, new_images, storage)


@router.delete("/{post_id}")
def delete_board(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), storage: BaseStorage = Depends(get_storage_manager)):
    return community_service.delete_board(post_id, db, current_user, storage)


@router.post("/{post_id}/like", response_model=dict)
def toggle_post_like(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.toggle_post_like(post_id, db, current_user)


@router.get("/{post_id}/is_liked", response_model=dict)
def check_post_liked_status(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.check_post_liked_status(post_id, db, current_user)

# ---------------------- 댓글 ----------------------
@router.post("/{post_id}/comments", response_model=CommentSchema)
def create_comment(post_id: int, comment: CommentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.create_comment(post_id, comment, db, current_user)


@router.get("/{post_id}/comments", response_model=list[CommentSchema])
def get_all_comment(post_id: int, db: Session = Depends(get_db)):
    return community_service.get_all_comment(post_id, db)


@router.patch("/comments/{comment_id}", response_model=CommentSchema)
def update_comment(comment_id: int, comment_update: CommentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.update_comment(comment_id, comment_update, db, current_user)


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.delete_comment(comment_id, db, current_user)


@router.get("/comments/{comment_id}/replies", response_model=List[CommentResponse])
def read_replies(comment_id: int, db: Session = Depends(get_db)):
    return community_service.read_replies(comment_id, db)


@router.post("/comments/{comment_id}/like", response_model=dict)
def toggle_comment_like(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.toggle_comment_like(comment_id, db, current_user)


@router.get("/comments/{comment_id}/is_liked", response_model=dict)
def check_comment_liked_status(comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.check_comment_liked_status(comment_id, db, current_user)


@router.get("/me/bookmarked", response_model=List[PostSearchResponse])
def get_my_bookmarked_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    return community_service.get_my_bookmarked_posts(current_user, db, page, page_size)


@router.get("/me/posts", response_model=List[PostSearchResponse])
def get_my_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100)
):
    return community_service.get_my_posts(current_user, db, page, page_size)


@router.get("/me/posts/recent", response_model=List[PostSearchResponse])
def get_my_recent_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return community_service.get_my_recent_posts(current_user, db)


@router.get("/me/bookmarked/recent", response_model=List[PostSearchResponse])
def get_my_recent_bookmarked_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return community_service.get_my_recent_bookmarked_posts(current_user, db)


@router.post("/{post_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def bookmark_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.bookmark_post(post_id, db, current_user)


@router.delete("/{post_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def unbookmark_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return community_service.unbookmark_post(post_id, db, current_user)

class IsBookmarked(BaseModel):
    is_bookmarked: bool

@router.get("/{post_id}/is-bookmarked", status_code=status.HTTP_200_OK, response_model=IsBookmarked)
def is_bookmarked(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return community_service.is_bookmarked(post_id, current_user, db)
