from __future__ import annotations

from collections import defaultdict
import hashlib
from datetime import datetime, timezone

from django.core.cache import cache

from .provider_factory import get_weather_provider
from .providers.base import WeatherPoint


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

    start_datetime = parse_iso_utc(start_time if isinstance(start_time, str) else start_time.isoformat())
    normalized_start = start_datetime.isoformat()
    rounded_points = [(round(lat, 4), round(lon, 4)) for lat, lon in points]
    coordinates_hash = hashlib.sha256(repr(rounded_points).encode('utf-8')).hexdigest()[:20]
    cache_key = f'weather:{coordinates_hash}:{normalized_start}:{hours}'
    cached = cache.get(cache_key)
    if cached is not None:
        return [WeatherPoint(**item) for item in cached]

    results = get_weather_provider().weather(
        rounded_points,
        time_start=normalized_start,
        hours=hours,
    )
    cache.set(cache_key, [item.__dict__ for item in results], timeout=60 * 10)
    return results


def index_weather_by_location(
    weather_points: list[WeatherPoint],
) -> dict[tuple[float, float], list[WeatherPoint]]:
    """Group forecast samples by rounded coordinate to keep lookup bounded."""
    grouped: dict[tuple[float, float], list[WeatherPoint]] = defaultdict(list)
    for point in weather_points:
        grouped[(round(point.latitude, 4), round(point.longitude, 4))].append(point)
    for samples in grouped.values():
        samples.sort(key=lambda item: parse_iso_utc(item.timestamp))
    return dict(grouped)


def weather_for_checkpoint(
    weather_points: list[WeatherPoint] | dict[tuple[float, float], list[WeatherPoint]],
    eta_utc: datetime,
    *,
    latitude: float,
    longitude: float,
) -> WeatherPoint | None:
    """Return nearest-time weather for this coordinate, or None outside forecast coverage."""
    if isinstance(weather_points, dict):
        matching_location = weather_points.get((round(latitude, 4), round(longitude, 4)), [])
    else:
        matching_location = [
            item for item in weather_points
            if round(item.latitude, 4) == round(latitude, 4)
            and round(item.longitude, 4) == round(longitude, 4)
        ]
    if not matching_location:
        return None

    target = eta_utc.astimezone(timezone.utc)
    nearest = min(matching_location, key=lambda item: abs(parse_iso_utc(item.timestamp) - target))
    if abs(parse_iso_utc(nearest.timestamp) - target).total_seconds() > 30 * 60:
        return None
    return nearest
