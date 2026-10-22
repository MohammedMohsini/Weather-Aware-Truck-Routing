from __future__ import annotations

import os
import math

import httpx

from .base import ProviderError, RouteResult, RoutingProvider
from .http_client import request_with_retries


class OpenRouteProvider(RoutingProvider):
    """OpenRouteService-backed routing provider."""

    def route(self, origin: tuple[float, float], destination: tuple[float, float], *, alternatives: bool = True) -> list[RouteResult]:
        api_key = os.getenv('ORS_API_KEY')
        if not api_key:
            raise ProviderError('Routing is unavailable: configure ORS_API_KEY on the backend host.', status_code=503)

        return self._request_routes(
            [[origin[1], origin[0]], [destination[1], destination[0]]],
            api_key,
            alternatives=alternatives,
        )

    def route_via_waypoint(
        self,
        origin: tuple[float, float],
        waypoint: tuple[float, float],
        destination: tuple[float, float],
    ) -> list[RouteResult]:
        """Request a road route through a waypoint to add distinct alternatives."""
        api_key = os.getenv('ORS_API_KEY')
        if not api_key:
            raise ProviderError('Routing is unavailable: configure ORS_API_KEY on the backend host.', status_code=503)

        return self._request_routes(
            [
                [origin[1], origin[0]],
                [waypoint[1], waypoint[0]],
                [destination[1], destination[0]],
            ],
            api_key,
            alternatives=False,
        )

    @staticmethod
    def _request_routes(
        coordinates: list[list[float]],
        api_key: str,
        *,
        alternatives: bool,
    ) -> list[RouteResult]:
        payload: dict[str, object] = {
            'coordinates': coordinates,
            'units': 'mi',
            'instructions': False,
        }
        if alternatives:
            payload['alternative_routes'] = {
                'target_count': 3,
                'weight_factor': 1.4,
                'share_factor': 0.6,
            }
        response = request_with_retries(
            httpx.post,
            'https://api.openrouteservice.org/v2/directions/driving-car/geojson',
            json=payload,
            headers={'Authorization': api_key},
            timeout=20.0,
        )
        if response.status_code >= 400:
            raise ProviderError('Routing request failed.', status_code=response.status_code, details={'body': response.text})

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError('Routing provider returned invalid JSON.', status_code=502) from exc
        if not isinstance(data, dict):
            raise ProviderError('Routing provider returned an invalid response.', status_code=502)
        features = data.get('features', [])
        if not isinstance(features, list):
            raise ProviderError('Routing provider returned invalid route data.', status_code=502)
        routes: list[RouteResult] = []
        if not features:
            return routes

        for index, feature in enumerate(features[:3]):
            if not isinstance(feature, dict):
                raise ProviderError('Routing provider returned an invalid route.', status_code=502)
            route_geometry = feature.get('geometry')
            properties = feature.get('properties')
            if not isinstance(route_geometry, dict) or not isinstance(properties, dict):
                raise ProviderError('Routing provider returned an invalid route.', status_code=502)
            geometry = route_geometry.get('coordinates')
            if not isinstance(geometry, list) or len(geometry) < 2:
                continue
            if any(
                not isinstance(point, list)
                or len(point) < 2
                or not isinstance(point[0], (int, float))
                or not isinstance(point[1], (int, float))
                or not math.isfinite(point[0])
                or not math.isfinite(point[1])
                or not -180 <= point[0] <= 180
                or not -90 <= point[1] <= 90
                for point in geometry
            ):
                raise ProviderError('Routing provider returned invalid route coordinates.', status_code=502)
            route_points = [[point[1], point[0]] for point in geometry]
            summary = properties.get('summary')
            summary = summary if isinstance(summary, dict) else {}
            try:
                distance = float(summary['distance'])
                duration_value = float(summary['duration'])
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderError('Routing provider returned invalid route metrics.', status_code=502) from exc
            if (
                not math.isfinite(distance)
                or not math.isfinite(duration_value)
                or distance <= 0
                or duration_value <= 0
            ):
                raise ProviderError('Routing provider returned invalid route metrics.', status_code=502)
            duration_seconds = int(duration_value)
            if duration_seconds < 1:
                raise ProviderError('Routing provider returned invalid route metrics.', status_code=502)
            route_name = summary.get('name')
            routes.append(
                RouteResult(
                    route_id=f'ors-route-{index + 1}',
                    geometry=route_points,
                    total_distance_miles=distance,
                    total_duration_seconds=duration_seconds,
                    summary=route_name if isinstance(route_name, str) and route_name else 'OpenRouteService driving route',
                )
            )
        return routes
