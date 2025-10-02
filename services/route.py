
from fastapi import HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from starlette import status

from models import Route, User
import schemas.route as route_schema

def get_routes(db: Session) -> List[route_schema.Route]:
    query = db.query(Route)
    routes = query.all()
    return routes

def get_my_routes(
    db: Session,
    current_user: User,
    page: int,
    page_size: int
) -> List[route_schema.Route]:
    skip = (page - 1) * page_size
    routes = db.query(Route).filter(Route.user_id == current_user.id).order_by(Route.created_at.desc()).offset(skip).limit(page_size).all()
    return routes

def get_route_by_id(route_id: int, db: Session) -> route_schema.Route:
    route = db.query(Route).filter(Route.id == route_id).first()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return route

def get_route_as_gpx(route_id: int, db: Session) -> Response:
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


import math

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate the bearing between two points."""
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    dLon = lon2 - lon1

    x = math.sin(dLon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)

    initial_bearing = math.atan2(x, y)

    return math.degrees(initial_bearing)

def get_turn_points(route_id: int, db: Session) -> List[dict]:
    """Get the points where the direction changes in a route."""
    route = get_route_by_id(route_id, db)

    if not route.points_json or len(route.points_json) < 3:
        return []

    turn_points = []
    old_bearing = calculate_bearing(
        route.points_json[0]["lat"],
        route.points_json[0]["lon"],
        route.points_json[1]["lat"],
        route.points_json[1]["lon"],
    )

    for i in range(1, len(route.points_json) - 1):
        lat1 = route.points_json[i]["lat"]
        lon1 = route.points_json[i]["lon"]
        lat2 = route.points_json[i + 1]["lat"]
        lon2 = route.points_json[i + 1]["lon"]

        # Calculate distance to avoid detecting turns for very small movements
        distance = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111320 # Approximate meters

        if distance < 10: # Ignore small movements
            continue

        new_bearing = calculate_bearing(lat1, lon1, lat2, lon2)

        bearing_diff = abs(new_bearing - old_bearing)
        if bearing_diff > 180:
            bearing_diff = 360 - bearing_diff

        if bearing_diff > 30: # Threshold for turn detection
            turn_points.append(route.points_json[i])

        old_bearing = new_bearing

    return turn_points

def update_route(
    route_id: int,
    route_update: route_schema.RouteUpdate,
    db: Session,
    current_user: User
) -> route_schema.Route:
    route = db.query(Route).filter(Route.id == route_id).first()

    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

    if route.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this route")

    if route_update.name is not None:
        route.name = route_update.name
    if route_update.points_json is not None:
        route.points_json = route_update.points_json

    db.commit()
    db.refresh(route)
    return route
