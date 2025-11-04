
from fastapi import HTTPException
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from zoneinfo import ZoneInfo

from zoneinfo import ZoneInfo



from models import Report, User, Route

from models.calender import Stamps

from schemas.report import ReportResponse, AllReportResponse, ReportCreate, ReportSummary, ReportUpdate, ReportLev



def measureStamp(db: Session, user_id: int) :
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())

    total_distance = db.query(func.sum(Report.distance)).filter(
        Report.user_id == user_id,
        Report.created_at >= start_of_day,
        Report.created_at <= end_of_day
    ).scalar() or 0

    stamp_level = 0
    if total_distance >= 15000:
        stamp_level = 5
    elif total_distance >= 12000:
        stamp_level = 4
    elif total_distance >= 9000:
        stamp_level = 3
    elif total_distance >= 6000:
        stamp_level = 2
    elif total_distance >= 3000:
        stamp_level = 1

    if stamp_level > 0:
        existing_stamp = db.query(Stamps).filter(
            Stamps.user_id == user_id,
            func.date(Stamps.date) == today
        ).first()

        if existing_stamp:
            existing_stamp.stamp_lev = stamp_level
            db.commit()
            db.refresh(existing_stamp)
        else:
            new_stamp = Stamps(
                user_id=user_id,
                stamp_lev=stamp_level,
                date=datetime.now(ZoneInfo("Asia/Seoul"))
            )
            db.add(new_stamp)
            db.commit()
            db.refresh(new_stamp)

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

    measureStamp(db, current_user.id)

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


def get_report_summary(db: Session, current_user: User, get_period: int, end_date: datetime) -> ReportSummary:
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
    highest_speed = max(report.highest_speed for report in reports)
    total_kal = sum(report.kcal for report in reports)

    return ReportSummary(
        routes_taken_count=routes_taken_count,
        total_activity_time_formatted=total_activity_time_formatted,
        total_activity_distance_km=total_activity_distance_km,
        max_speed = highest_speed,
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

def get_report_lev(db: Session, current_user: User) -> ReportLev:
    total_distance = db.query(func.sum(Report.distance)).filter(Report.user_id == current_user.id).scalar() or 0
    total_distance_km = total_distance / 1000

    levels = {
        1: {"name": "탐험가", "exp_needed": 0},
        2: {"name": "항해자", "exp_needed": 200},
        3: {"name": "개척자", "exp_needed": 600},
        4: {"name": "정복자", "exp_needed": 1400},
        5: {"name": "창조자", "exp_needed": 3000}
    }

    current_level = 1
    for lev, data in levels.items():
        if total_distance_km >= data["exp_needed"]:
            current_level = lev
        else:
            break

    next_level_exp = levels[current_level + 1]["exp_needed"] if current_level < 5 else levels[5]["exp_needed"]

    return ReportLev(
        lev=levels[current_level]["name"],
        exp=total_distance_km,
        next_lev_exp=next_level_exp
    )

