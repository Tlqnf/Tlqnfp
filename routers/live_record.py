
from fastapi import APIRouter, WebSocket, Query, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from utils.auth import get_current_user
from services.live_record import LiveRecordingService, start_live_recording_session as start_session_service

router = APIRouter()

@router.get("/start-session", response_model=dict)
async def start_live_recording_session(
    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user)
):
    return start_session_service(db, current_user)

@router.websocket("/ws/record-route")
async def record_route(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    live_record_service = LiveRecordingService(db)
    await live_record_service.handle_websocket(websocket, token)
