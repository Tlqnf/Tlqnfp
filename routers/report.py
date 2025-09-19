from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from zoneinfo import ZoneInfo # For timezone

from models import Report, User, Route
from schemas.report import ReportResponse, AllReportResponse, ReportCreate, WeeklyReportSummary
from database import get_db
from utils.auth import get_current_user

router = APIRouter(prefix="/report", tags=["report"])

@router.post("/", response_model=AllReportResponse)
def create_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new report for an existing route.
    """
    # Check if the route exists
    route = db.query(Route).filter(Route.id == report_data.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail=f"Route with id {report_data.route_id} not found")

    new_report = Report(
        **report_data.dict(),
        user_id=current_user.id
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report

@router.get("/", response_model=List[ReportResponse])
def get_all_reports(db: Session = Depends(get_db)):
    """
    Get all reports. (Note: This might need admin privileges in a real app)
    """
    reports = db.query(Report).all()
    return reports


@router.get("/by-user", response_model=List[ReportResponse])
def get_reports_by_user(
        user_id: Optional[int] = Query(None, description="Filter reports by User ID (defaults to current user)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a list of reports for a specific user.
    If user_id is not provided, it defaults to the current authenticated user's ID.
    A user can only retrieve their own reports.
    """
    target_user_id = user_id if user_id is not None else current_user.id

    # Authorization check: A user can only query for their own reports
    if target_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 리포트를 조회할 권한이 없습니다.")

    query = db.query(Report).filter(
        Report.user_id == target_user_id
    )

    reports = query.all()

    if not reports:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 리포트를 찾을 수 없습니다.")

    return reports


@router.get("/by-route-user", response_model=List[ReportResponse])
def get_reports_by_route_and_user(
        route_id: int = Query(..., description="Filter reports by Route ID"),
        user_id: Optional[int] = Query(None, description="Filter reports by User ID (defaults to current user) "),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get a list of reports filtered by Route ID and optionally by User ID.
    If user_id is not provided, it defaults to the current authenticated user's ID.
    A user can only retrieve their own reports.
    """
    target_user_id = user_id if user_id is not None else current_user.id

    # Authorization check: A user can only query for their own reports
    if target_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 리포트를 조회할 권한이 없습니다.")

    query = db.query(Report).filter(
        Report.route_id == route_id,
        Report.user_id == target_user_id
    )

    reports = query.all()

    if not reports:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 리포트를 찾을 수 없습니다.")

    return reports


@router.get("/weekly_summary", response_model=WeeklyReportSummary)
def get_weekly_report_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    한 주간 유저의 리포트를 합산하여 기록을 반환합니다.
    경로 탄 횟수, 활동 시간, 활동 거리 데이터 포함.
    """
    end_date = datetime.now(ZoneInfo("Asia/Seoul")) # Use KST for consistency
    start_date = end_date - timedelta(days=7)

    reports = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.created_at >= start_date,
        Report.created_at <= end_date
    ).all()

    if not reports:
        return WeeklyReportSummary(
            routes_taken_count=0,
            total_activity_time_hours=0,
            total_activity_time_remaining_minutes=0,
            total_activity_distance_km=0
        )

    routes_taken_count = len(reports)
    total_activity_time_total_minutes = sum(report.health_time for report in reports) / 60 # Convert seconds to minutes (float)
    total_activity_time_hours = int(total_activity_time_total_minutes // 60)
    total_activity_time_remaining_minutes = round(total_activity_time_total_minutes % 60)
    total_activity_distance_km = sum(report.distance for report in reports) / 1000 # Convert meters to kilometers

    return WeeklyReportSummary(
        routes_taken_count=routes_taken_count,
        total_activity_time_hours=total_activity_time_hours,
        total_activity_time_remaining_minutes=total_activity_time_remaining_minutes,
        total_activity_distance_km=total_activity_distance_km
    )


@router.get("/{report_id}", response_model=AllReportResponse)
def get_report_by_id(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get a specific report by ID.
    Only the author of the report can access it.
    """
    report = db.query(Report).options(
        selectinload(Report.route)
    ).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    
    # Authorization check
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="리포트를 볼 권한이 없습니다.")

    return report



