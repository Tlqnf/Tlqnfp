import os
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from collections import deque
from database import SessionLocal
from models import Route, Report, User
from utill.tracking_calculator import TrackingSession
from dotenv import load_dotenv
from utils.auth import get_user_from_token

load_dotenv()

router = APIRouter()

VALHALLA_URL = os.getenv("VALHALLA_URL")
SLIDING_WINDOW_SIZE = 10

class GPSData(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

def decode_polyline(polyline_str):
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            
            if result & 1:
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append({'lat': lat / 1E6, 'lon': lng / 1E6})

    return coordinates

async def correct_path_with_valhalla(points: list[GPSData]):
    if not VALHALLA_URL or not points or len(points) < 2:
        return []

    valhalla_payload = {
        "shape": [{"lat": p.lat, "lon": p.lon} for p in points],
        "costing": "bicycle",
        "shape_match": "map_snap",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{VALHALLA_URL}/trace_attributes", json=valhalla_payload, timeout=10.0)
            response.raise_for_status()
            traced_data = response.json()
            
            if traced_data.get("shape"):
                return decode_polyline(traced_data["shape"])
            return []
        except httpx.RequestError as e:
            print(f"Valhalla API request failed: {e}")
            return []

@router.websocket("/ws/record-route")
async def record_route(websocket: WebSocket, token: str = Query(...)):
    # 1. Authenticate user and create initial route in one session
    new_route_id = None
    with SessionLocal() as db:
        try:
            user = await get_user_from_token(token=token, db=db)
            # 2. Initialize a new route with user_id
            new_route = Route(points_json=[], user_id=user.id)
            db.add(new_route)
            db.commit()
            db.refresh(new_route)
            new_route_id = new_route.id
        except HTTPException as e: # Catch the HTTPException
            print(f"Authentication failed: Status Code {e.status_code}, Detail: {e.detail}")
            await websocket.close(code=1008) # Policy violation
            return

    await websocket.accept()
    await websocket.send_json({"route_id": new_route_id})

    session = TrackingSession()
    recent_raw_points = deque(maxlen=SLIDING_WINDOW_SIZE)

    try:
        # 3. Loop to receive points
        while True:
            data = await websocket.receive_json()
            gps_point = GPSData(**data)
            recent_raw_points.append(gps_point)

            if len(recent_raw_points) < 2:
                await websocket.send_json({"status": "Gathering initial points..."})
                continue

            # 4. Correct path and update session
            corrected_trace = await correct_path_with_valhalla(list(recent_raw_points))
            if corrected_trace:
                latest_corrected_point = corrected_trace[-1]
                session.add_corrected_point(latest_corrected_point)

                # 5. Send live stats to client
                live_stats = session.get_live_stats()
                response_data = {**live_stats, "corrected_coordinate": latest_corrected_point}
                await websocket.send_json(response_data)

    except WebSocketDisconnect:
        # 6. Save final data on disconnect in a new session
        with SessionLocal() as db:
            if session.corrected_points:
                # Omit 'time' from the points to avoid JSON serialization error
                final_points = [
                    {k: v for k, v in p.items() if k != 'time'} for p in session.corrected_points
                ]
                route_to_update = db.query(Route).filter(Route.id == new_route_id).first()
                if route_to_update:
                    route_to_update.points_json = final_points
                    start_point_data = {k: v for k, v in session.corrected_points[0].items() if k != 'time'}
                    end_point_data = {k: v for k, v in session.corrected_points[-1].items() if k != 'time'}
                    route_to_update.start_point = start_point_data
                    route_to_update.end_point = end_point_data
                    db.add(route_to_update)

                # Save final report
                final_report_data = session.get_final_report_data()
                if final_report_data:
                    new_report = Report(**final_report_data, route_id=new_route_id, user_id=user.id)
                    db.add(new_report)
                
                db.commit()
                print(f"Session for route {new_route_id} ended. Route and Report saved.")
            else:
                # If no points were ever corrected, delete the empty route
                route_to_delete = db.query(Route).filter(Route.id == new_route_id).first()
                if route_to_delete:
                    db.delete(route_to_delete)
                    db.commit()
                print(f"Session for route {new_route_id} ended. No data, route deleted.")

    except Exception as e:
        print(f"An error occurred: {e}")
