from fastapi import APIRouter, Depends, HTTPException, status
from httpx import request
from sqlalchemy.orm import Session
from database import get_db
from models import Route
import httpx
import os
from pydantic import BaseModel # Import BaseModel for response model
import json

router = APIRouter(prefix="/navigation", tags=["navigation"])

VALHALLA_URL = os.getenv("VALHALLA_URL")

def filter_navigation_instructions(data):
    instructions = data.get("instructions", [])

    # Filter out duplicate consecutive instructions
    filtered_instructions = []
    last_instruction = None
    for instruction in instructions:
        if instruction != last_instruction:
            filtered_instructions.append(instruction)
            last_instruction = instruction

    # Remove all "목적지에 도착했습니다." except for the last one
    final_instructions = []
    destination_message = "목적지에 도착했습니다."

    # Count occurrences of the destination message
    destination_count = filtered_instructions.count(destination_message)

    if destination_count > 0:
        # Add all instructions except the destination message
        for instruction in filtered_instructions:
            if instruction != destination_message:
                final_instructions.append(instruction)
        # Add the destination message once at the very end
        final_instructions.append(destination_message)
    else:
        final_instructions = filtered_instructions

    data["instructions"] = final_instructions
    return data

async def get_valhalla_route(locations: list[dict], costing: str = "bicycle"):
    if not VALHALLA_URL:
        raise HTTPException(status_code=500, detail="Valhalla URL not configured.")

    payload = {
        "locations": locations,
        "costing": costing,
        "directions_options": {"units": "meters"}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{VALHALLA_URL}/route", json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Valhalla routing failed: {e}")


def parse_valhalla_instructions(valhalla_response: dict) -> dict:
    if not valhalla_response or not valhalla_response.get("trip"):
        return {"summary": "No route found.", "instructions": []}

    # --- Translation Data ---
    translation_map = {
        "Bike north.": "북쪽으로 주행하세요.",
        "Bike northwest.": "북서쪽으로 주행하세요.",
        "Bike west.": "서쪽으로 주행하세요.",
        "Bike southwest.": "남서쪽으로 주행하세요.",
        "Bike south.": "남쪽으로 주행하세요.",
        "Bike southeast.": "남동쪽으로 주행하세요.",
        "Bike east.": "동쪽으로 주행하세요.",
        "Bike northeast.": "북동쪽으로 주행하세요.",
        "Bear left.": "왼쪽으로 도세요.",
        "Bear right.": "오른쪽으로 도세요.",
        "Turn left.": "좌회전하세요.",
        "Turn right.": "우회전하세요.",
        "Make a sharp left.": "급좌회전하세요.",
        "Make a sharp right.": "급우회전하세요.",
        "Continue.": "계속 주행하세요.",
        "You have arrived at your destination.": "목적지에 도착했습니다.",
        "Keep left at the fork.": "갈림길에서 좌측을 유지하세요.",
        "Keep right at the fork.": "갈림길에서 우측을 유지하세요.",
    }
    translation_prefixes = {
        "Bike north on": "북쪽으로 계속 주행하세요:",
        "Bear left onto": "좌회전하여 진입하세요:",
        "Bear right onto": "우회전하여 진입하세요:",
        "Bike northwest on": "북서쪽으로 계속 주행하세요:",
        "Bike west on": "서쪽으로 계속 주행하세요:",
        "Bike southwest on": "남서쪽으로 계속 주행하세요:",
        "Bike south on": "남쪽으로 계속 주행하세요:",
        "Bike southeast on": "남동쪽으로 계속 주행하세요:",
        "Bike east on": "동쪽으로 계속 주행하세요:",
        "Bike northeast on": "북동쪽으로 계속 주행하세요:",
        "Turn left onto": "좌회전하여 진입하세요:",
        "Turn right onto": "우회전하여 진입하세요:",
        "Turn left to stay on": "좌회전하여 유지하세요:",
        "Turn right to stay on": "우회전하여 유지하세요:",
        "Continue on": "계속 주행하세요:",
        "Bear left to stay on": "왼쪽으로 주행하여 유지하세요:",
        "Bear right to stay on": "오른쪽으로 주행하여 유지하세요:",
        "Keep left to stay on": "왼쪽 차선을 유지하세요:",
        "Keep right to stay on": "오른쪽 차선을 유지하세요:",
        "Keep left to take": "왼쪽으로 진입하세요:",
        "Keep right to take": "오른쪽으로 진입하세요:",
    }

    def translate(text: str) -> str:
        # Handle instructions with street names
        for prefix, translation in translation_prefixes.items():
            if text.startswith(prefix):
                # Extract street name and rest of the instruction
                rest_of_instruction = text[len(prefix):].strip()
                return f"{translation} {rest_of_instruction}"
        
        # Handle exact matches
        return translation_map.get(text, text)

    # --- Parsing Logic ---
    trip = valhalla_response["trip"]
    legs = trip["legs"]
    
    total_time = 0
    total_distance = 0
    instructions = []

    for leg in legs:
        total_time += leg["summary"]["time"]
        total_distance += leg["summary"]["length"]
        maneuvers = leg["maneuvers"]

        for i, maneuver in enumerate(maneuvers):
            instruction_text = maneuver["instruction"]
            distance = maneuver["length"]
            maneuver_type = maneuver["type"]

            # Translate the instruction
            translated_instruction = translate(instruction_text)

            # Handle destination maneuvers (types 4, 5, 6)
            if maneuver_type in [4, 5, 6]:
                # Only add the instruction if it's the very last maneuver of the whole trip
                if i == len(maneuvers) - 1:
                    instructions.append(translated_instruction)
            else:
                distance_in_meters = int(distance * 1000)
                formatted_instruction = f"{distance_in_meters}m 앞 {translated_instruction}"
                instructions.append(formatted_instruction)

    total_distance_km = round(total_distance, 2)
    total_time_minutes = round(total_time / 60, 1)
    summary = f"총 거리: {total_distance_km} km, 예상 소요 시간: {total_time_minutes} 분"

    return {
        "summary": summary,
        "total_distance_km": total_distance_km,
        "total_time_minutes": total_time_minutes,
        "instructions": instructions
    }

class GuideRouteRequest(BaseModel):
    route_id: int

# --- Endpoints ---
@router.post("/guide-route")
async def guide_existing_route(request: GuideRouteRequest, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == request.route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")
    
    # Convert stored points_json to Valhalla locations format
    # NOTE: Temporarily removing 'type: "through"' to debug Valhalla 500 error.
    # This will likely cause multiple "You have arrived" messages to appear.
    locations = []
    for point in route.points_json:
        locations.append({"lat": point["lat"], "lon": point["lon"]})

    if len(locations) < 2:
        raise HTTPException(status_code=400, detail="경로 안내를 위한 충분한 좌표가 없습니다.")

    valhalla_response = await get_valhalla_route(locations)
    parsed_instructions = parse_valhalla_instructions(valhalla_response)
    
    # Apply filtering logic
    filtered_parsed_instructions = filter_navigation_instructions(parsed_instructions)
    
    return filtered_parsed_instructions

class GuideDestinationRequest(BaseModel):
    start_lat: float
    start_lon: float
    destination_lat: float
    destination_lon: float

@router.post("/guide-destination")
async def guide_to_destination(request: GuideDestinationRequest,
                               db: Session = Depends(get_db)):
    # For shortest path, we need a starting point. 
    # For now, let's assume the user provides a start point or we get it from a live session.
    # For this example, let's use a dummy start point or require it.
    # TODO: Integrate with user's current location or a specified start point.
    
    # Dummy start point for demonstration
    start_location = {"lat": request.start_lat, "lon": request.start_lon} # Example: Seoul City Hall
    end_location = {"lat": request.destination_lat, "lon": request.destination_lon}

    locations = [start_location, end_location]

    valhalla_response = await get_valhalla_route(locations)
    parsed_instructions = parse_valhalla_instructions(valhalla_response)

    # Apply filtering logic
    filtered_parsed_instructions = filter_navigation_instructions(parsed_instructions)

    return filtered_parsed_instructions

class GeocodeResponse(BaseModel):
    lat: float
    lon: float

@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_address(query: str):
    # Placeholder for a geocoding API call
    # In a real application, you would integrate with a service like:
    # Google Geocoding API, Naver Maps API, Kakao Maps API, or OpenStreetMap Nominatim

    # Example: Using a dummy response for "Seoul City Hall"
    if "서울시청" in query:
        return {"lat": 37.5665, "lon": 126.9780}
    elif "남산타워" in query:
        return {"lat": 37.5512, "lon": 126.9882}
    else:
        raise HTTPException(status_code=404, detail="Location not found.")