from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class GuideRouteRequest(BaseModel):
    route_id: int

class GuideDestinationRequest(BaseModel):
    start_lat: float
    start_lon: float
    destination_lat: float
    destination_lon: float

class GeocodeResponse(BaseModel):
    lat: float
    lon: float
