from __future__ import annotations

import math
from dataclasses import replace

from django.core.cache import cache

from .providers.base import ProviderError, RouteResult
from .provider_factory import get_routing_provider
from .route_service import haversine_miles, route_distance_miles


def generate_3_routes(origin: tuple[float, float], destination: tuple[float, float]) -> list[RouteResult]:
    """Return three distinct provider-routed alternatives or raise a clear provider error."""
    cache_key = (
        f'routes:v2:{origin[0]:.4f},{origin[1]:.4f}:'
        f'{destination[0]:.4f},{destination[1]:.4f}'
    )
    cached_routes = cache.get(cache_key)
    if cached_routes is not None:
        return [
            replace(RouteResult(**route), route_id=f'route-{index + 1}')
            for index, route in enumerate(cached_routes)
        ]

    provider = get_routing_provider()
    routes = _distinct_routes(provider.route(origin, destination, alternatives=True))

    route_via_waypoint = getattr(provider, 'route_via_waypoint', None)
    if len(routes) < 3 and callable(route_via_waypoint):
        for offset_miles in (15.0, -15.0, 30.0, -30.0, 45.0, -45.0):
            waypoint = _offset_midpoint(origin, destination, offset_miles)
            for candidate in route_via_waypoint(origin, waypoint, destination):
                if _is_distinct(candidate, routes):
                    routes.append(candidate)
                    if len(routes) == 3:
                        break
            if len(routes) == 3:
                break

    if len(routes) < 3:
        raise ProviderError(
            f'The routing provider returned only {len(routes)} distinct driving routes; three are required.',
            status_code=502,
        )

    result = [replace(route, route_id=f'route-{index + 1}') for index, route in enumerate(routes[:3])]
    cache.set(cache_key, [route.__dict__ for route in result], timeout=60 * 60)
    return result


def _offset_midpoint(
    origin: tuple[float, float],
    destination: tuple[float, float],
    offset_miles: float,
) -> tuple[float, float]:
    """Find a waypoint a given perpendicular distance from the trip midpoint."""
    mid_lat = (origin[0] + destination[0]) / 2
    mid_lon = (origin[1] + destination[1]) / 2
    longitude_scale = max(math.cos(math.radians(mid_lat)), 0.01)
    dx = (destination[1] - origin[1]) * 69.0 * longitude_scale
    dy = (destination[0] - origin[0]) * 69.0
    length = math.hypot(dx, dy)
    if length == 0:
        raise ValueError('Origin and destination must be different locations.')

    perpendicular_x = -dy / length
    perpendicular_y = dx / length
    return (
        mid_lat + perpendicular_y * offset_miles / 69.0,
        mid_lon + perpendicular_x * offset_miles / (69.0 * longitude_scale),
    )


def _distinct_routes(routes: list[RouteResult]) -> list[RouteResult]:
    """Remove duplicate or near-identical provider geometries."""
    distinct: list[RouteResult] = []
    for route in routes:
        if route.geometry and _is_distinct(route, distinct):
            distinct.append(route)
    return distinct


def _is_distinct(candidate: RouteResult, routes: list[RouteResult]) -> bool:
    candidate_distance = candidate.total_distance_miles or route_distance_miles(candidate.geometry)
    for existing in routes:
        existing_distance = existing.total_distance_miles or route_distance_miles(existing.geometry)
        if not existing.geometry or not candidate.geometry:
            continue
        if abs(candidate_distance - existing_distance) / max(candidate_distance, existing_distance, 1.0) > 0.02:
            continue

        sample_count = min(10, len(candidate.geometry), len(existing.geometry))
        if sample_count < 2:
            continue
        separations = []
        for index in range(sample_count):
            candidate_point = candidate.geometry[index * (len(candidate.geometry) - 1) // (sample_count - 1)]
            existing_point = existing.geometry[index * (len(existing.geometry) - 1) // (sample_count - 1)]
            separations.append(haversine_miles(tuple(candidate_point), tuple(existing_point)))
        if sum(separations) / len(separations) < 5:
            return False
    return True
