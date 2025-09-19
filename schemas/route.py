from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from schemas.report import ReportListResponse
from schemas.base import Route, SEOUL_TZ, convert_datetime_to_korea_time

class RouteUpdate(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None

class RoutePointsResponse(BaseModel):
    points_json: Optional[List[Dict[str, Any]]] = []

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}

class RouteWithReportsResponse(BaseModel):
    points_json: Optional[List[Dict[str, Any]]] = []
    reports: List['ReportListResponse'] = []

    class Config:
        from_attributes = True
        json_encoders = {datetime: convert_datetime_to_korea_time}