
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from zoneinfo import ZoneInfo

from models import Report, User, Route
from schemas.report import ReportResponse, AllReportResponse, ReportCreate, ReportSummary, ReportUpdate

def create_report(
    report_data: ReportCreate,
    db: Session,
    current_user: User
) -> AllReportResponse:
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

def get_all_reports(db: Session) -> List[ReportResponse]:
    reports = db.query(Report).all()
    return reports

def get_reports_by_user(
    user_id: Optional[int],
    db: Session,
    current_user: User
) -> List[ReportResponse]:
    target_user_id = user_id if user_id is not None else current_user.id

    if target_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 리포트를 조회할 권한이 없습니다.")

    query = db.query(Report).filter(
        Report.user_id == target_user_id
    )

    reports = query.all()

    if not reports:
        raise HTTPException(status_code=404, detail="해당 조건에 맞는 리포트를 찾을 수 없습니다.")

    return reports

def get_reports_by_route_and_user(
    route_id: int,
    user_id: Optional[int],
    db: Session,
    current_user: User
) -> List[ReportResponse]:
    target_user_id = user_id if user_id is not None else current_user.id

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

# report 통계


def get_report_summary(db: Session, current_user: User, get_period: int) -> ReportSummary:
    end_date = datetime.now(ZoneInfo("Asia/Seoul"))
    if(get_period == 1):
        start_date = end_date
    elif(get_period == 2):
        start_date = end_date - timedelta(days=7)
    elif(get_period == 3):
        import calendar
        start_date = end_date - timedelta(calendar.monthrange(end_date.year, end_date.month)[1])


    reports = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.created_at >= start_date,
        Report.created_at <= end_date
    ).all()

    if not reports:
        return ReportSummary()

    routes_taken_count = len(reports)
    total_activity_time_seconds = sum(report.health_time for report in reports)
    hours = total_activity_time_seconds // 3600
    minutes = (total_activity_time_seconds % 3600) // 60
    seconds = total_activity_time_seconds % 60
    total_activity_time_formatted = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    total_activity_distance_km = sum(report.distance for report in reports) / 1000
    total_kal = sum(report.kcal for report in reports)

    return ReportSummary(
        routes_taken_count=routes_taken_count,
        total_activity_time_formatted=total_activity_time_formatted,
        total_activity_distance_km=total_activity_distance_km,
        total_kal=total_kal
    )

def get_report_by_id(report_id: int, db: Session, current_user: User) -> AllReportResponse:
    report = db.query(Report).options(
        selectinload(Report.route)
    ).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="리포트를 볼 권한이 없습니다.")

    return report

def update_report(
    report_id: int,
    report_update: ReportUpdate,
    db: Session,
    current_user: User
) -> AllReportResponse:
    report = db.query(Report).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="리포트를 찾을 수 없습니다.")

    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="리포트를 수정할 권한이 없습니다.")

    update_data = report_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(report, key, value)

    db.commit()
    db.refresh(report)
    return report
