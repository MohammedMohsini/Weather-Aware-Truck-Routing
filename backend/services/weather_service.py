from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
from django.core.cache import cache

from .providers.base import ProviderError, WeatherPoint


def parse_iso_utc(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to UTC."""
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_weather_for_points(
    points: list[tuple[float, float]],
    *,
    start_time: str | datetime,
    hours: int = 48,
) -> list[WeatherPoint]:
    """Fetch hourly weather for multiple coordinates in one Open-Meteo request."""
    if not points:
        return []

    normalized_start = start_time if isinstance(start_time, str) else start_time.isoformat()
    cache_key = f'weather:{len(points)}:{normalized_start}:{hours}:{hash(tuple(sorted(points)))}'
    cached = cache.get(cache_key)
    if cached is not None:
        return [WeatherPoint(**item) for item in cached]

    coordinates = [(lat, lon) for lat, lon in points]
    params = {
        'latitude': [lat for lat, _ in coordinates],
        'longitude': [lon for _, lon in coordinates],
        'hourly': ['wind_speed_10m', 'rain', 'snowfall'],
        'wind_speed_unit': 'mph',
        'precipitation_unit': 'inch',
        'timezone': 'UTC',
        'start_hour': normalized_start,
        'end_hour': (parse_iso_utc(normalized_start) + timedelta(hours=hours)).isoformat(),
    }

    response = httpx.get('https://api.open-meteo.com/v1/forecast', params=params, timeout=20.0)
    if response.status_code >= 400:
        raise ProviderError('Weather forecast request failed', status_code=response.status_code, details={'body': response.text})

    payload = response.json()
    hourly = payload.get('hourly', {})
    time_points = hourly.get('time', [])
    wind_values = hourly.get('wind_speed_10m', [])
    rain_values = hourly.get('rain', [])
    snow_values = hourly.get('snowfall', [])

    if not time_points:
        raise ProviderError('Open-Meteo did not return hourly weather data.', status_code=502)

    results: list[WeatherPoint] = []
    for idx, (lat, lon) in enumerate(coordinates):
        for i, timestamp in enumerate(time_points):
            results.append(
                WeatherPoint(
                    latitude=lat,
                    longitude=lon,
                    timestamp=timestamp,
                    wind_mph=float(wind_values[i]) if i < len(wind_values) else 0.0,
                    rain_in_hr=float(rain_values[i]) if i < len(rain_values) else 0.0,
                    snow_in_hr=float(snow_values[i]) if i < len(snow_values) else 0.0,
                )
            )

    cache.set(cache_key, [item.__dict__ for item in results], timeout=60 * 10)
    return results


def weather_for_checkpoint(weather_points: list[WeatherPoint], eta_utc: datetime) -> WeatherPoint | None:
    """Return the nearest available weather sample for a checkpoint ETA."""
    if not weather_points:
        return None

    target = eta_utc.astimezone(timezone.utc)
    nearest = min(weather_points, key=lambda item: abs(parse_iso_utc(item.timestamp) - target))
    return nearest
