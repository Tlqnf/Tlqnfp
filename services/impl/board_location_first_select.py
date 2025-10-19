from sqlalchemy.orm import Session
from typing import List
import math

from services.abstract.board_select import BoardSelectService
from models import Post, Report, Route
from schemas.community import PostResponse


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


class LocationBoardSelectService(BoardSelectService):
    def select(self, db: Session, user_lat: float, user_lon: float) -> List[PostResponse]:
        posts_with_location = (
            db.query(Post, Route.start_point)
            .join(Report, Post.report_id == Report.id)
            .join(Route, Report.route_id == Route.id)
            .filter(Route.start_point.isnot(None))
            .all()
        )

        if not posts_with_location:
            return []

        # Calculate distance for each post
        posts_with_distance = []
        for post, start_point in posts_with_location:
            if start_point and 'latitude' in start_point and 'longitude' in start_point:
                post_lat = start_point['latitude']
                post_lon = start_point['longitude']
                distance = haversine(user_lat, user_lon, post_lat, post_lon)
                posts_with_distance.append((post, distance))

        # Sort posts by distance
        sorted_posts = sorted(posts_with_distance, key=lambda x: x[1])

        # Prepare response
        response = [PostResponse.model_validate(post) for post, distance in sorted_posts]

        return response
