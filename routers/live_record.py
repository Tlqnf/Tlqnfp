import os
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from collections import deque
from database import SessionLocal, get_db
from models import Route, Report, User
from utill.tracking_calculator import TrackingSession
from dotenv import load_dotenv
from utils.auth import get_user_from_token, get_current_user
import json

load_dotenv()

router = APIRouter()

VALHALLA_URL = os.getenv("VALHALLA_URL")
SLIDING_WINDOW_SIZE = 10

class GPSData(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


@router.get("/start-session", response_model=dict)
async def start_live_recording_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates placeholder Route and Report records to start a live recording session.
    Returns the IDs of the created Route and Report.
    """
    try:
        # 1. Create placeholder Route
        new_route = Route(points_json=[], user_id=current_user.id)
        db.add(new_route)
        db.commit()
        db.refresh(new_route)

        # 2. Create placeholder Report
        new_report = Report(route_id=new_route.id, user_id=current_user.id)
        db.add(new_report)
        db.commit()
        db.refresh(new_report)

        return {
            "status": "session_started",
            "route_id": new_route.id,
            "report_id": new_report.id
        }
    except Exception as e:
        db.rollback()  # Rollback in case of error
        print(f"Error during start_live_recording_session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start recording session"
        )


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


def save_session_data(db: Session, session: TrackingSession, route_id: int, report_id: int):
    """Helper function to update route and report data."""
    route_to_update = db.query(Route).filter(Route.id == route_id).first()
    report_to_update = db.query(Report).filter(Report.id == report_id).first()

    if not route_to_update or not report_to_update:
        print(f"Error: Route {route_id} or Report {report_id} not found for saving.")
        return

    if session.corrected_points:
        # Update Route
        final_points = [
            {k: v for k, v in p.items() if k != 'time'} for p in session.corrected_points
        ]
        route_to_update.points_json = final_points
        route_to_update.start_point = {k: v for k, v in session.corrected_points[0].items() if k != 'time'}
        route_to_update.end_point = {k: v for k, v in session.corrected_points[-1].items() if k != 'time'}
        db.add(route_to_update)

        # Report is intentionally left empty as per user request.
        
        db.commit()
        print(f"Session for route {route_id} ended. Route updated, Report left empty.")
    else:
        # If no data, delete the created placeholder records
        db.delete(route_to_update)
        db.delete(report_to_update)
        db.commit()
        print(f"Session for route {route_id} ended. No data, placeholder records deleted.")


@router.websocket("/ws/record-route")
async def record_route(websocket: WebSocket, token: str = Query(...)):
    db = SessionLocal()
    user = None
    new_route_id = None
    new_report_id = None

    try:
        # 1. Authenticate user
        user = await get_user_from_token(token=token, db=db)

        # 2. Create placeholder Route and Report
        new_route = Route(points_json=[], user_id=user.id)
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        new_route_id = new_route.id

        new_report = Report(route_id=new_route_id, user_id=user.id)
        db.add(new_report)
        db.commit()
        db.refresh(new_report)
        new_report_id = new_report.id

    except HTTPException as e:
        print(f"Authentication failed: Status Code {e.status_code}, Detail: {e.detail}")
        await websocket.close(code=1008)
        db.close()
        return
    except Exception as e:
        print(f"Error during initial setup: {e}")
        await websocket.close(code=1011)
        db.close()
        return

    await websocket.accept()
    # 3. Send the new IDs to the client immediately
    await websocket.send_json({
        "status": "session_started",
        "route_id": new_route_id,
        "report_id": new_report_id
    })

    session = TrackingSession()
    recent_raw_points = deque(maxlen=SLIDING_WINDOW_SIZE)
    
    try:
        # 4. Loop to receive GPS data
        while True:
            data = await websocket.receive_json()
            gps_point = GPSData(**data)
            recent_raw_points.append(gps_point)

            if len(recent_raw_points) < 2:
                await websocket.send_json({"status": "Gathering initial points..."})
                continue

            corrected_trace = await correct_path_with_valhalla(list(recent_raw_points))
            if corrected_trace:
                latest_corrected_point = corrected_trace[-1]
                session.add_corrected_point(latest_corrected_point)

                live_stats = session.get_live_stats()
                response_data = {**live_stats, "corrected_coordinate": latest_corrected_point}
                await websocket.send_json(response_data)

    except WebSocketDisconnect:
        # 5. On disconnect, save the final data to the existing records
        print(f"Client disconnected for route {new_route_id}. Saving data.")
        save_session_data(db, session, new_route_id, new_report_id)

    except Exception as e:
        print(f"An error occurred in WebSocket for route {new_route_id}: {e}")

    finally:
        db.close()
        print(f"WebSocket connection closed for route {new_route_id}.")