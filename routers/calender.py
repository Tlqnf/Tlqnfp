from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends, Query, Path
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas.calender import StampRecord, CalenderStampData

from services import calender as calender_service
from utils.auth import get_current_user

router = APIRouter(prefix="/calender", tags=["calender"])

@router.get("/stamp-report/{date}", response_model = StampRecord)
async def getStampReport (
        db: Session = Depends(get_db),
        date: str = Path(..., pattern = r"^\d{4}-\d{2}$"),
        current_user: User = Depends(get_current_user),
):
    try:
        date = datetime.strptime(date, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format please use YYYY-MM string")
    return calender_service.getStampRecord(db, current_user.id, date)


@router.get("/month-stamp/{date}", response_model = list[CalenderStampData])
async def getMonthStamp (
        db: Session = Depends(get_db),
        date: str = Path(..., pattern = r"^\d{4}-\d{2}$"),
        current_user: User = Depends(get_current_user),
):
    try:
        date = datetime.strptime(date, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format please use YYYY-MM string")
    return calender_service.getStampData(db, current_user.id, False, date)

@router.get("/today-stamp")
async def getTodayStamp (
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return calender_service.getStampData(db, current_user.id, True)

@router.get("/count-of-stamp")
async def getCountOfStamp (
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return calender_service.findAllCountStamp(db, current_user.id)



