from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from .base import BaseProvider, GeocodeResult, ProviderError, RouteResult, WeatherPoint


class OpenMeteoProvider(BaseProvider):
    """Open-Meteo weather provider using a single batched request."""

    def geocode(self, query: str) -> list[GeocodeResult]:
        raise NotImplementedError('Geocoding is provided by the Nominatim adapter.')

    def route(self, origin: tuple[float, float], destination: tuple[float, float], *, alternatives: bool = True) -> list[RouteResult]:
        raise NotImplementedError('Routing is provided by the routing adapter.')

    def weather(self, coordinates: list[tuple[float, float]], *, time_start: str, hours: int) -> list[WeatherPoint]:
        if not coordinates:
            return []

        start_dt = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(hours=hours)

        params = {
            'latitude': [lat for lat, _ in coordinates],
            'longitude': [lon for _, lon in coordinates],
            'hourly': ['wind_speed_10m', 'rain', 'snowfall'],
            'wind_speed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'UTC',
            'start_hour': start_dt.isoformat(),
            'end_hour': end_dt.isoformat(),
        }
        response = httpx.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=20.0)
        if response.status_code >= 400:
            raise ProviderError('Weather forecast request failed.', status_code=response.status_code, details={'body': response.text})

        payload = response.json()
        hourly = payload.get('hourly', {})
        timestamps = hourly.get('time', [])
        winds = hourly.get('wind_speed_10m', [])
        rain = hourly.get('rain', [])
        snow = hourly.get('snowfall', [])

        results: list[WeatherPoint] = []
        for idx, (lat, lon) in enumerate(coordinates):
            for hour_idx, timestamp in enumerate(timestamps):
                results.append(
                    WeatherPoint(
                        latitude=lat,
                        longitude=lon,
                        timestamp=timestamp,
                        wind_mph=float(winds[hour_idx]) if hour_idx < len(winds) else 0.0,
                        rain_in_hr=float(rain[hour_idx]) if hour_idx < len(rain) else 0.0,
                        snow_in_hr=float(snow[hour_idx]) if hour_idx < len(snow) else 0.0,
                    )
                )
        return results
