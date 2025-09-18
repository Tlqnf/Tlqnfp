from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from schemas.base import Route, convert_datetime_to_korea_time

class ReportCreate(BaseModel):
    route_id: int
    health_time: int = 0
    half_time: int = 0
    distance: int = 0
    kcal: int = 0
    average_speed: float = 0.0
    highest_speed: float = 0.0
    average_face: float = 0.0
    highest_face: float = 0.0
    cumulative_high: int = 0
    highest_high: int = 0
    lowest_high: int = 0
    increase_slope: float = 0.0
    decrease_slope: float = 0.0

class ReportResponse(BaseModel):
    id: int
    health_time: int
    average_speed: float
    kcal: int
    cumulative_high: int
    increase_slope: float
    created_at: datetime
    route_id: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class AllReportResponse(BaseModel):
    id: int
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: int
    kcal: int
    average_speed: float
    highest_speed: float
    average_face: float
    highest_face: float
    cumulative_high: int
    highest_high: int
    lowest_high: int
    increase_slope: float
    decrease_slope: float
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class ReportListResponse(BaseModel):
    distance: int
    average_speed: float
    health_time: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class ReportWithRouteResponse(BaseModel):
    id: int
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: int
    kcal: int
    average_speed: float
    highest_speed: float
    average_face: float
    highest_face: float
    cumulative_high: int
    highest_high: int
    lowest_high: int
    increase_slope: float
    decrease_slope: float
    user_id: int
    created_at: datetime
    route: "Route"

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}

class WeeklyReportSummary(BaseModel):
    routes_taken_count: int
    total_activity_time_minutes: float
    total_activity_distance_km: float