from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from schemas.base import Route, convert_datetime_to_korea_time

class ReportCreate(BaseModel):
    route_id: int
    health_time: int = 0
    half_time: int = 0
    distance: float = 0.0
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
    distance: float # Changed from int to float

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class AllReportResponse(BaseModel):
    id: int
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: float
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
    distance: float # Changed from int to float
    average_speed: float
    health_time: int

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time} # Add this

class ReportWithRouteResponse(BaseModel):
    id: int
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: float
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

class ReportSummary(BaseModel):
    routes_taken_count: int = 0
    total_activity_time_formatted: str = "00:00:00"
    total_activity_distance_km: float = 0
    max_speed: float = 0
    total_kal: int = 0


class ReportLev(BaseModel):
    lev: str
    exp: int
    next_lev_exp: int

class MonthlyDistanceComparison(BaseModel):
    change_type: int
    distance_change: float




class ReportUpdate(BaseModel):
    health_time: Optional[int] = None
    half_time: Optional[int] = None
    distance: Optional[float] = None
    kcal: Optional[int] = None
    average_speed: Optional[float] = None
    highest_speed: Optional[float] = None
    average_face: Optional[float] = None
    highest_face: Optional[float] = None
    cumulative_high: Optional[int] = None
    highest_high: Optional[int] = None
    lowest_high: Optional[int] = None
    increase_slope: Optional[float] = None
    decrease_slope: Optional[float] = None
