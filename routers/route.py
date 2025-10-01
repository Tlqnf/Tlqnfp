from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User
import schemas.route as route_schema
from utils.auth import get_current_user
from services import route as route_service

router = APIRouter(
    prefix="/routes",
    tags=["routes"]
)

@router.get("", response_model=List[route_schema.Route])
def get_routes(db: Session = Depends(get_db)):
    """저장된 모든 경로의 목록을 JSON 형식으로 반환합니다."""
    return route_service.get_routes(db)

@router.get("/me", response_model=List[route_schema.Route])
def get_my_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=100)
):
    """특정 유저의 경로를 불러올 수 있음."""
    return route_service.get_my_routes(db, current_user, page, page_size)

@router.get("/{route_id}", response_model=route_schema.Route)
def get_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """ID로 특정 경로를 조회합니다."""
    return route_service.get_route_by_id(route_id, db)


@router.get("/{route_id}/gpx")
def get_route_as_gpx(route_id: int, db: Session = Depends(get_db)):
    """ID로 특정 경로를 조회하여 GPX 파일로 반환합니다."""
    return route_service.get_route_as_gpx(route_id, db)


@router.patch("/{route_id}", response_model=route_schema.Route)
def update_route(
    route_id: int,
    route_update: route_schema.RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """경로의 이름이나 태그를 수정합니다."""
    return route_service.update_route(route_id, route_update, db, current_user)