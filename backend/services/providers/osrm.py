from __future__ import annotations

import math

import httpx

from .base import ProviderError, RouteResult, RoutingProvider
from .http_client import request_with_retries

METERS_PER_MILE = 1609.344
OSRM_ROUTE_URL = 'https://router.project-osrm.org/route/v1/driving/'


class OsrmProvider(RoutingProvider):
    """Public OSRM driving router; no API key is required."""

    def route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        alternatives: bool = True,
    ) -> list[RouteResult]:
        return self._request_routes(
            [origin, destination],
            alternatives='3' if alternatives else 'false',
        )

    def route_via_waypoint(
        self,
        origin: tuple[float, float],
        waypoint: tuple[float, float],
        destination: tuple[float, float],
    ) -> list[RouteResult]:
        """Request a driving route passing through an additional coordinate."""
        return self._request_routes([origin, waypoint, destination], alternatives='false')

    @staticmethod
    def _request_routes(
        coordinates: list[tuple[float, float]],
        *,
        alternatives: str,
    ) -> list[RouteResult]:
        coordinate_path = ';'.join(f'{longitude},{latitude}' for latitude, longitude in coordinates)
        try:
            response = request_with_retries(
                httpx.get,
                f'{OSRM_ROUTE_URL}{coordinate_path}',
                params={
                    'alternatives': alternatives,
                    'overview': 'full',
                    'geometries': 'geojson',
                    'steps': 'false',
                },
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            raise ProviderError('OSRM routing service could not be reached.', status_code=502) from exc

        if response.status_code >= 400:
            raise ProviderError('OSRM routing request failed.', status_code=502)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError('OSRM returned invalid JSON.', status_code=502) from exc
        if not isinstance(payload, dict) or payload.get('code') != 'Ok':
            message = payload.get('message') if isinstance(payload, dict) else None
            raise ProviderError(
                message if isinstance(message, str) else 'OSRM could not find a driving route.',
                status_code=422,
            )

        raw_routes = payload.get('routes')
        if not isinstance(raw_routes, list):
            raise ProviderError('OSRM returned invalid route data.', status_code=502)

        routes: list[RouteResult] = []
        for index, raw_route in enumerate(raw_routes[:3]):
            if not isinstance(raw_route, dict):
                raise ProviderError('OSRM returned an invalid route.', status_code=502)
            geometry = raw_route.get('geometry')
            coordinates_geojson = geometry.get('coordinates') if isinstance(geometry, dict) else None
            if not isinstance(coordinates_geojson, list) or len(coordinates_geojson) < 2:
                raise ProviderError('OSRM returned route geometry with too few points.', status_code=502)
            if any(
                not isinstance(point, list)
                or len(point) < 2
                or not isinstance(point[0], (int, float))
                or not isinstance(point[1], (int, float))
                or not math.isfinite(point[0])
                or not math.isfinite(point[1])
                or not -180 <= point[0] <= 180
                or not -90 <= point[1] <= 90
                for point in coordinates_geojson
            ):
                raise ProviderError('OSRM returned invalid route coordinates.', status_code=502)

            try:
                distance_meters = float(raw_route['distance'])
                duration_seconds = float(raw_route['duration'])
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError('OSRM returned invalid route metrics.', status_code=502) from exc
            if (
                not math.isfinite(distance_meters)
                or not math.isfinite(duration_seconds)
                or distance_meters <= 0
                or duration_seconds <= 0
            ):
                raise ProviderError('OSRM returned invalid route metrics.', status_code=502)

            routes.append(
                RouteResult(
                    route_id=f'osrm-route-{index + 1}',
                    geometry=[[point[1], point[0]] for point in coordinates_geojson],
                    total_distance_miles=distance_meters / METERS_PER_MILE,
                    total_duration_seconds=round(duration_seconds),
                    summary='OSRM driving route',
                )
            )
        return routes
