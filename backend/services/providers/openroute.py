from __future__ import annotations

import os

import httpx

from .base import BaseProvider, GeocodeResult, ProviderError, RouteResult, WeatherPoint


class OpenRouteProvider(BaseProvider):
    """OpenRouteService-backed routing provider."""

    def geocode(self, query: str) -> list[GeocodeResult]:
        raise NotImplementedError('Geocoding is provided by the Nominatim adapter.')

    def route(self, origin: tuple[float, float], destination: tuple[float, float], *, alternatives: bool = True) -> list[RouteResult]:
        api_key = os.getenv('ORS_API_KEY')
        if not api_key:
            # This fallback is intentionally lightweight and does not require external credentials.
            return [
                RouteResult(
                    route_id='ors-fallback-1',
                    geometry=[[origin[0], origin[1]], [destination[0], destination[1]]],
                    total_distance_miles=0.0,
                    total_duration_seconds=0,
                    summary='ORS fallback route',
                )
            ]

        payload = {
            'coordinates': [[origin[1], origin[0]], [destination[1], destination[0]]],
            'format': 'geojson',
            'units': 'mi',
            'options': {'avoid_features': ['ferries', 'tollways']},
            'api_key': api_key,
        }
        response = httpx.post(
            'https://api.openrouteservice.org/v2/directions/driving-car/geojson',
            json=payload,
            headers={'Authorization': api_key},
            timeout=20.0,
        )
        if response.status_code >= 400:
            raise ProviderError('Routing request failed.', status_code=response.status_code, details={'body': response.text})

        data = response.json()
        features = data.get('features', [])
        routes: list[RouteResult] = []
        if not features:
            return routes

        for index, feature in enumerate(features[:3]):
            geometry = feature.get('geometry', {}).get('coordinates', [])
            route_points = [[point[1], point[0]] for point in geometry]
            properties = feature.get('properties', {})
            routes.append(
                RouteResult(
                    route_id=f'ors-route-{index + 1}',
                    geometry=route_points,
                    total_distance_miles=float(properties.get('summary', {}).get('distance', 0.0) or 0.0),
                    total_duration_seconds=int(properties.get('summary', {}).get('duration', 0) or 0),
                    summary='OpenRouteService route',
                )
            )
        return routes

    def weather(self, coordinates: list[tuple[float, float]], *, time_start: str, hours: int) -> list[WeatherPoint]:
        raise NotImplementedError('Weather fetching is implemented by the weather provider adapter.')
