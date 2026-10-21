from __future__ import annotations

import httpx

from .base import BaseProvider, GeocodeResult, ProviderError, RouteResult, WeatherPoint


class NominatimProvider(BaseProvider):
    """Geocoding provider using Nominatim."""

    def geocode(self, query: str) -> list[GeocodeResult]:
        params = {
            'q': query,
            'format': 'jsonv2',
            'limit': 5,
            'addressdetails': 1,
        }
        response = httpx.get(
            'https://nominatim.openstreetmap.org/search',
            params=params,
            timeout=10.0,
            headers={'User-Agent': 'WeatherAwareTruckRouting/1.0'},
        )
        if response.status_code >= 400:
            raise ProviderError(
                'Geocoding request failed.',
                status_code=response.status_code,
                details={'body': response.text},
            )

        payload = response.json()
        results: list[GeocodeResult] = []
        for item in payload:
            try:
                results.append(
                    GeocodeResult(
                        display_name=item.get('display_name', query),
                        latitude=float(item['lat']),
                        longitude=float(item['lon']),
                    )
                )
            except (TypeError, KeyError, ValueError):
                continue
        return results

    def route(self, origin: tuple[float, float], destination: tuple[float, float], *, alternatives: bool = True) -> list[RouteResult]:
        raise NotImplementedError('Routing provider is implemented in openroute.py.')

    def weather(self, coordinates: list[tuple[float, float]], *, time_start: str, hours: int) -> list[WeatherPoint]:
        raise NotImplementedError('Weather fetching is implemented by the weather provider adapter.')
