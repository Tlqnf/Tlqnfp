from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel
from services.navigation import (
    get_navigation_for_route,
    get_navigation_for_destination,
    geocode_address as geocode_address_service
)

router = APIRouter(prefix="/navigation", tags=["navigation"])

class GuideRouteRequest(BaseModel):
    route_id: int

@router.post("/guide-route")
async def guide_existing_route(request: GuideRouteRequest, db: Session = Depends(get_db)):
    return await get_navigation_for_route(request.route_id, db)

class GuideDestinationRequest(BaseModel):
    start_lat: float
    start_lon: float
    destination_lat: float
    destination_lon: float

@router.post("/guide-destination")
async def guide_to_destination(request: GuideDestinationRequest):
    return await get_navigation_for_destination(
        start_lat=request.start_lat,
        start_lon=request.start_lon,
        destination_lat=request.destination_lat,
        destination_lon=request.destination_lon
    )

class GeocodeResponse(BaseModel):
    lat: float
    lon: float

@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_address(query: str):
    return geocode_address_service(query)
