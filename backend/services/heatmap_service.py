from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from services.risk_service import RISK_LEVEL_NAMES, classify_checkpoint
from services.route_service import build_checkpoints, route_distance_miles
from services.weather_service import (
    get_weather_for_points,
    index_weather_by_location,
    parse_iso_utc,
    weather_for_checkpoint,
)

HEATMAP_CORRIDOR_MILES = 12.0
MAX_HEATMAP_POINTS = 300
FORECAST_HOURS = 48


def build_corridor_points(
    route_geometries: list[list[list[float]]],
) -> list[dict[str, Any]]:
    """Sample a bounded three-lane corridor around each route, at roughly 20-mile spacing."""
    points_by_coordinate: dict[tuple[float, float], dict[str, Any]] = {}
    for route_index, geometry in enumerate(route_geometries):
        route_id = f'route-{route_index + 1}'
        distance = route_distance_miles(geometry)
        interval = max(20.0, distance / 32.0)
        checkpoints = build_checkpoints(geometry, interval_miles=interval)
        centers = [(point.latitude, point.longitude) for point in checkpoints]

        for index, center in enumerate(centers):
            previous = centers[max(0, index - 1)]
            following = centers[min(len(centers) - 1, index + 1)]
            tangent = _normalized_tangent(previous, following, center[0])
            candidate_coordinates = [
                center,
                _offset_coordinate(center, tangent, HEATMAP_CORRIDOR_MILES),
                _offset_coordinate(center, tangent, -HEATMAP_CORRIDOR_MILES),
            ]
            for latitude, longitude in candidate_coordinates:
                key = (round(latitude, 4), round(longitude, 4))
                existing = points_by_coordinate.setdefault(
                    key,
                    {
                        'latitude': key[0],
                        'longitude': key[1],
                        'route_ids': [],
                    },
                )
                if route_id not in existing['route_ids']:
                    existing['route_ids'].append(route_id)

    points = list(points_by_coordinate.values())
    if len(points) > MAX_HEATMAP_POINTS:
        stride = math.ceil(len(points) / MAX_HEATMAP_POINTS)
        points = points[::stride][:MAX_HEATMAP_POINTS]
    return points


def generate_heatmap(
    *,
    route_geometries: list[list[list[float]]],
    start_time: str,
    load_lb: float,
) -> dict[str, Any]:
    """Fetch one batched forecast and classify each corridor point at hours 0 through 48."""
    start_utc = parse_iso_utc(start_time)
    sample_points = build_corridor_points(route_geometries)
    if not sample_points:
        raise ValueError('Route geometries did not produce any heatmap sample points.')

    coordinates = [(point['latitude'], point['longitude']) for point in sample_points]
    forecast = get_weather_for_points(coordinates, start_time=start_utc, hours=FORECAST_HOURS)
    weather_index = index_weather_by_location(forecast)

    hours = [
        {
            'hour': hour,
            'timestamp_utc': (start_utc + timedelta(hours=hour)).isoformat(),
        }
        for hour in range(FORECAST_HOURS + 1)
    ]
    result_points = []
    for point_index, point in enumerate(sample_points):
        hourly = []
        for hour in hours:
            eta = datetime.fromisoformat(hour['timestamp_utc']).astimezone(timezone.utc)
            weather = weather_for_checkpoint(
                weather_index,
                eta,
                latitude=point['latitude'],
                longitude=point['longitude'],
            )
            if weather is None:
                raise ValueError(
                    f'No weather forecast is available for heatmap point {point_index} '
                    f'at {hour["timestamp_utc"]}. Choose a start time within the forecast window.'
                )
            risk = classify_checkpoint(
                index=hour['hour'],
                latitude=point['latitude'],
                longitude=point['longitude'],
                wind_mph=weather.wind_mph,
                rain_in_hr=weather.rain_in_hr,
                snow_in_hr=weather.snow_in_hr,
                load_lb=load_lb,
            )
            hourly.append({
                **hour,
                'wind_mph': weather.wind_mph,
                'rain_in_hr': weather.rain_in_hr,
                'snow_in_hr': weather.snow_in_hr,
                'risk_level': risk.final_risk,
                'risk': risk.level_name,
                'reason': risk.reason,
            })
        result_points.append({**point, 'hourly': hourly})

    return {
        'hours': hours,
        'points': result_points,
        'forecast_hours': FORECAST_HOURS,
        'load_lb': load_lb,
    }


def _normalized_tangent(
    previous: tuple[float, float],
    following: tuple[float, float],
    latitude: float,
) -> tuple[float, float]:
    longitude_scale = max(math.cos(math.radians(latitude)), 0.01)
    dx = (following[1] - previous[1]) * 69.0 * longitude_scale
    dy = (following[0] - previous[0]) * 69.0
    length = math.hypot(dx, dy)
    if length == 0:
        return 1.0, 0.0
    return dx / length, dy / length


def _offset_coordinate(
    center: tuple[float, float],
    tangent: tuple[float, float],
    offset_miles: float,
) -> tuple[float, float]:
    """Offset perpendicular to a local route tangent in miles."""
    dx, dy = tangent
    latitude, longitude = center
    longitude_scale = max(math.cos(math.radians(latitude)), 0.01)
    return (
        latitude - dx * offset_miles / 69.0,
        longitude + dy * offset_miles / (69.0 * longitude_scale),
    )
