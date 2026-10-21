from __future__ import annotations

from datetime import datetime

from .providers.base import RouteResult
from .provider_factory import get_routing_provider
from .route_service import build_checkpoints, route_distance_miles


def generate_3_routes(origin: tuple[float, float], destination: tuple[float, float]) -> list[RouteResult]:
    """Return up to three route alternatives, using the configured provider or a local fallback."""
    provider = get_routing_provider()
    routes = provider.route(origin, destination, alternatives=True)
    if len(routes) >= 3:
        return routes[:3]

    # Fallback if the provider is unavailable or returns too few alternatives.
    base_lat = (origin[0] + destination[0]) / 2
    base_lon = (origin[1] + destination[1]) / 2
    offsets = [
        (0.0, 0.0),
        (0.25, -0.35),
        (-0.25, 0.35),
    ]

    fallback: list[RouteResult] = []
    for index, (lat_offset, lon_offset) in enumerate(offsets[:3]):
        mid_lat = base_lat + lat_offset
        mid_lon = base_lon + lon_offset
        route_geometry = [
            [origin[0], origin[1]],
            [mid_lat, mid_lon],
            [destination[0], destination[1]],
        ]
        dist = route_distance_miles(route_geometry)
        fallback.append(
            RouteResult(
                route_id=f'fallback-route-{index + 1}',
                geometry=[[lat, lon] for lat, lon in route_geometry],
                total_distance_miles=dist if dist > 0 else 1.0,
                total_duration_seconds=max(int(dist * 60), 1800),
                summary='fallback route',
            )
        )
    return fallback[:3]


def route_checkpoints_for_trip(
    route_geometry: list[list[float]],
    *,
    interval_miles: int,
    departure_time: str | datetime,
    total_duration_seconds: int,
):
    """Create checkpoints for a route geometry and a chosen interval."""
    points = [(float(lat), float(lng)) for lat, lng in route_geometry]
    return build_checkpoints(points, interval_miles=interval_miles, departure_time=departure_time, total_duration_seconds=total_duration_seconds)
