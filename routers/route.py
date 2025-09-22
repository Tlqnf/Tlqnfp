from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Route, User
import schemas.route as route_schema
from utils.auth import get_current_user

router = APIRouter(
    prefix="/routes",
    tags=["routes"]
)

@router.get("", response_model=List[route_schema.Route])
def get_routes(db: Session = Depends(get_db), tags: Optional[List[str]] = Query(None)):
    """저장된 모든 경로의 목록을 JSON 형식으로 반환합니다. 태그를 사용하여 필터링할 수 있습니다."""
    if tags and len(tags) > 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can query with a maximum of 3 tags.")

    query = db.query(Route)
    if tags:
        query = query.filter(Route.tags.contains(tags))
    routes = query.all()
    return routes





@router.get("/me", response_model=List[route_schema.Route])
def get_my_routes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(4, ge=1, le=100)
):
    """특정 유저의 경로를 불러올 수 있음."""
    skip = (page - 1) * page_size
    routes = db.query(Route).filter(Route.user_id == current_user.id).order_by(Route.created_at.desc()).offset(skip).limit(page_size).all()
    return routes

@router.get("/{route_id}", response_model=route_schema.Route)
def get_route_by_id(route_id: int, db: Session = Depends(get_db)):
    """ID로 특정 경로를 조회합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.get("/{route_id}/gpx")
def get_route_as_gpx(route_id: int, db: Session = Depends(get_db)):
    """ID로 특정 경로를 조회하여 GPX 파일로 반환합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    if not route.points_json:
        raise HTTPException(status_code=404, detail="Route has no points to export")

    gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="NuclPedal" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Route {route.id}</name>
    <trkseg>
'''
    for point in route.points_json:
        gpx_content += f'      <trkpt lat="{point["lat"]}" lon="{point["lon"]}"></trkpt>\n'

    gpx_content += '''    </trkseg>
  </trk>
</gpx>'''

    return Response(
        content=gpx_content,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f"attachment; filename=route_{route_id}.gpx"}
    )


@router.patch("/{route_id}", response_model=route_schema.Route)
def update_route(
    route_id: int,
    route_update: route_schema.RouteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """경로의 이름이나 태그를 수정합니다."""
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    if route.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this route")

    if route_update.name is not None:
        route.name = route_update.name
    if route_update.tags is not None:
        if len(route_update.tags) > 3:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can add a maximum of 3 tags.")
        route.tags = route_update.tags

    db.commit()
    db.refresh(route)
    return route


