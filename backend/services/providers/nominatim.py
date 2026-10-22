from __future__ import annotations

import math

import httpx

from .base import GeocodeResult, GeocodingProvider, ProviderError
from .http_client import request_with_retries


class NominatimProvider(GeocodingProvider):
    """Geocoding provider using Nominatim."""

    def geocode(self, query: str) -> list[GeocodeResult]:
        params = {
            'q': query,
            'format': 'jsonv2',
            'limit': 5,
            'addressdetails': 1,
        }
        response = request_with_retries(
            httpx.get,
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

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError('Geocoding provider returned invalid JSON.', status_code=502) from exc
        if not isinstance(payload, list):
            raise ProviderError('Geocoding provider returned an invalid response.', status_code=502)
        results: list[GeocodeResult] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            try:
                latitude = float(item['lat'])
                longitude = float(item['lon'])
                if (
                    not math.isfinite(latitude)
                    or not math.isfinite(longitude)
                    or not -90 <= latitude <= 90
                    or not -180 <= longitude <= 180
                ):
                    continue
                display_name = item.get('display_name', query)
                if not isinstance(display_name, str):
                    display_name = query
                results.append(
                    GeocodeResult(
                        display_name=display_name,
                        latitude=latitude,
                        longitude=longitude,
                    )
                )
            except (TypeError, KeyError, ValueError):
                continue
        return results
