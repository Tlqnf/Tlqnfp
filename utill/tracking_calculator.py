
import math
from datetime import datetime, timezone
from typing import List, Dict, Any


def haversine_distance(p1: Dict[str, float], p2: Dict[str, float]) -> float:
    """Calculate the distance between two points in meters."""
    R = 6371e3  # Earth radius in meters
    lat1 = math.radians(p1['lat'])
    lat2 = math.radians(p2['lat'])
    delta_lat = math.radians(p2['lat'] - p1['lat'])
    delta_lon = math.radians(p2['lon'] - p1['lon'])

    a = (
        math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
        math.cos(lat1) * math.cos(lat2) *
        math.sin(delta_lon / 2) * math.sin(delta_lon / 2)
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # in meters


class TrackingSession:
    """Manages the state and calculations for a single tracking session."""

    def __init__(self):
        self.corrected_points: List[Dict[str, Any]] = []
        self.start_time: datetime = datetime.now(timezone.utc)

        # Report metrics
        self.distance: float = 0.0  # meters
        self.current_speed: float = 0.0  # m/s
        self.highest_speed: float = 0.0  # m/s
        self.cumulative_high: float = 0.0  # meters
        self.highest_high: float = -math.inf
        self.lowest_high: float = math.inf
        self.half_time: float = 0.0 # seconds
        self.total_pace: float = 0.0 # total pace for average calculation
        self.pace_count: int = 0 # count of pace values for average calculation
        self.highest_pace: float = 0.0 # min/km
        self.increasing_slopes: List[float] = []
        self.decreasing_slopes: List[float] = []

    def add_corrected_point(self, point: Dict[str, Any]):
        """Adds a new corrected point and updates all metrics."""
        point_with_time = {**point, 'time': datetime.now(timezone.utc)}

        if self.corrected_points:
            prev_point = self.corrected_points[-1]

            # Calculate half_time (rest time)
            # Check if the current point is essentially the same as the previous point
            if abs(point_with_time['lat'] - prev_point['lat']) < 1e-6 and \
               abs(point_with_time['lon'] - prev_point['lon']) < 1e-6:
                time_stationary = (point_with_time['time'] - prev_point['time']).total_seconds()
                self.half_time += time_stationary

            # Calculate distance delta
            dist_delta = haversine_distance(prev_point, point_with_time)
            self.distance += dist_delta

            # Calculate speed
            time_delta = (point_with_time['time'] - prev_point['time']).total_seconds()
            if time_delta > 0.5:  # Only calculate speed if time delta is meaningful
                speed = dist_delta / time_delta  # m/s
                self.current_speed = speed
                if speed > self.highest_speed:
                    self.highest_speed = speed

                # Calculate pace (minutes per kilometer)
                if dist_delta > 0:
                    pace_s_m = time_delta / dist_delta  # seconds per meter
                    pace_min_km = (pace_s_m * 1000) / 60 # minutes per kilometer
                    self.total_pace += pace_min_km
                    self.pace_count += 1
                    if pace_min_km > self.highest_pace:
                        self.highest_pace = pace_min_km
            else:
                self.current_speed = 0

            # Handle altitude metrics if 'ele' (elevation) is in point data
            if 'ele' in point:
                altitude = point['ele']
                if altitude > self.highest_high:
                    self.highest_high = altitude
                if altitude < self.lowest_high:
                    self.lowest_high = altitude

                prev_altitude = prev_point.get('ele', altitude)
                alt_delta = altitude - prev_altitude

                if alt_delta > 0:
                    self.cumulative_high += alt_delta

                # Calculate slope
                if dist_delta > 0:
                    slope = alt_delta / dist_delta
                    if slope > 0:
                        self.increasing_slopes.append(slope)
                    elif slope < 0:
                        self.decreasing_slopes.append(slope)

        self.corrected_points.append(point_with_time)

    def get_live_stats(self) -> Dict[str, Any]:
        """Returns a dictionary of current live metrics."""
        total_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        avg_speed = (self.distance / total_seconds) if total_seconds > 0 else 0

        return {
            "distance": self.distance,
            "current_speed": self.current_speed,
            "average_speed": avg_speed,
            "kcal": self.distance * 0.05,  # Simplified placeholder calculation
        }

    def get_final_report_data(self) -> Dict[str, Any]:
        """Calculates and returns the final report data."""
        if not self.corrected_points:
            return {}

        total_session_duration = (self.corrected_points[-1]['time'] - self.start_time).total_seconds()
        avg_speed = (self.distance / total_session_duration) if total_session_duration > 0 else 0

        health_time = total_session_duration - self.half_time

        average_pace = (self.total_pace / self.pace_count) if self.pace_count > 0 else 0
        average_increase_slope = (sum(self.increasing_slopes) / len(self.increasing_slopes)) if self.increasing_slopes else 0
        average_decrease_slope = (sum(self.decreasing_slopes) / len(self.decreasing_slopes)) if self.decreasing_slopes else 0

        return {
            "health_time": int(health_time),
            "half_time": int(self.half_time),
            "distance": int(self.distance),
            "kcal": int(self.distance * 0.05), # Simplified placeholder calculation
            "average_speed": avg_speed,
            "highest_speed": self.highest_speed,
            "average_face": average_pace,
            "highest_face": self.highest_pace,
            "cumulative_high": int(self.cumulative_high),
            "highest_high": int(self.highest_high if self.highest_high != -math.inf else 0),
            "lowest_high": int(self.lowest_high if self.lowest_high != math.inf else 0),
            "increase_slope": average_increase_slope,
            "decrease_slope": average_decrease_slope,
        }
