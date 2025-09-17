from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Route, User
import schemas.route as route_schema
from utils.auth import get_current_user

router = APIRouter(
    prefix="/routes",
    tags=["routes"]
)

@router.get("/", response_model=List[route_schema.Route])
def get_routes(db: Session = Depends(get_db)):
    """저장된 모든 경로의 목록을 JSON 형식으로 반환합니다."""
    routes = db.query(Route).all()
    return routes

@router.get("/me/bookmarked", response_model=List[route_schema.Route])
def get_my_bookmarked_routes(current_user: User = Depends(get_current_user)):
    """현재 사용자가 북마크한 모든 경로의 목록을 반환합니다."""
    return current_user.bookmarked_routes



@router.get("/me", response_model=List[route_schema.Route])
def get_my_routes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """특정 유저의 경로를 불러올 수 있음."""
    routes = db.query(Route).filter(Route.user_id == current_user.id).all()
    return routes

@router.get("/{route_id}", response_model=route_schema.Route)
def get_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """ID로 특정 경로를 조회합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.post("/{route_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def bookmark_route(route_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """특정 경로를 현재 사용자의 북마크에 추가합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
    
    if route in current_user.bookmarked_routes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route already bookmarked")

    current_user.bookmarked_routes.append(route)
    db.commit()

@router.delete("/{route_id}/bookmark", status_code=status.HTTP_204_NO_CONTENT)
def unbookmark_route(route_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """특정 경로를 현재 사용자의 북마크에서 제거합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    if route not in current_user.bookmarked_routes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route not bookmarked")

    current_user.bookmarked_routes.remove(route)
    db.commit()
