from datetime import datetime

from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from models import User
from schemas.report import ReportResponse, AllReportResponse, ReportCreate, ReportSummary, ReportUpdate, ReportLev, MonthlyDistanceComparison, DailyDistance
from database import get_db
from utils.auth import get_current_user
from services import report as report_service

router = APIRouter(prefix="/report", tags=["report"])

@router.post("", response_model=AllReportResponse)
def create_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return report_service.create_report(report_data, db, current_user)

@router.get("", response_model=List[ReportResponse])
def get_all_reports(db: Session = Depends(get_db)):
    return report_service.get_all_reports(db)


@router.get("/by-user", response_model=List[ReportResponse])
def get_reports_by_user(
        user_id: Optional[int] = Query(None, description="Filter reports by User ID (defaults to current user)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return report_service.get_reports_by_user(user_id, db, current_user)


@router.get("/by-route-user", response_model=List[ReportResponse])
def get_reports_by_route_and_user(
        route_id: int = Query(..., description="Filter reports by Route ID"),
        user_id: Optional[int] = Query(None, description="Filter reports by User ID (defaults to current user) "),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return report_service.get_reports_by_route_and_user(route_id, user_id, db, current_user)


@router.get("/weekly-summary", response_model=ReportSummary)
def get_weekly_report_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_report_summary(db, current_user,2, datetime.today())

@router.get("/monthly-summary", response_model=ReportSummary)
def get_monthly_report_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_report_summary(db, current_user, 3,datetime.today())

@router.get("/daily-summary/", response_model=ReportSummary)
def get_daily_report_summary(date: datetime = datetime.now() ,db: Session = Depends(get_db), current_user: User = Depends(get_current_user) ):

    return report_service.get_report_summary(db, current_user,1, date)


@router.get("/daily-distance", response_model=List[DailyDistance])
def get_last_week_daily_distance(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_last_week_daily_distance(db, current_user)


@router.get("/monthly-comparison", response_model=MonthlyDistanceComparison)
def get_monthly_distance_comparison(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_monthly_distance_comparison(db, current_user)


@router.get("/lev", response_model=ReportLev)
def get_report_lev(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_report_lev(db, current_user)


@router.get("/{report_id}", response_model=AllReportResponse)
def get_report_by_id(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return report_service.get_report_by_id(report_id, db, current_user)


@router.patch("/{report_id}", response_model=AllReportResponse)
def update_report(
    report_id: int,
    report_update: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return report_service.update_report(report_id, report_update, db, current_user)