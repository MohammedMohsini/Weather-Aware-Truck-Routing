from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import httpx

from .base import ProviderError, WeatherPoint, WeatherProvider
from .http_client import request_with_retries


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo weather provider using a single batched request."""

    def weather(self, coordinates: list[tuple[float, float]], *, time_start: str, hours: int) -> list[WeatherPoint]:
        if not coordinates:
            return []

        start_dt = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        start_dt = start_dt.astimezone(timezone.utc)
        end_dt = start_dt + timedelta(hours=hours)
        end_date = end_dt.date()
        params = {
            'latitude': ','.join(str(lat) for lat, _ in coordinates),
            'longitude': ','.join(str(lon) for _, lon in coordinates),
            'hourly': 'wind_speed_10m,rain,snowfall',
            'wind_speed_unit': 'mph',
            'precipitation_unit': 'inch',
            'timezone': 'UTC',
            'start_date': start_dt.date().isoformat(),
            'end_date': end_date.isoformat(),
        }
        response = request_with_retries(
            httpx.get,
            'https://api.open-meteo.com/v1/forecast',
            params=params,
            timeout=20.0,
        )
        if response.status_code >= 400:
            raise ProviderError('Weather forecast request failed.', status_code=response.status_code, details={'body': response.text})

        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError('Open-Meteo returned invalid JSON.', status_code=502) from exc
        location_payloads = payload if isinstance(payload, list) else [payload]
        if len(location_payloads) != len(coordinates) or any(
            not isinstance(location, dict) for location in location_payloads
        ):
            raise ProviderError(
                'Open-Meteo returned weather data for a different number of locations than requested.',
                status_code=502,
            )
        results: list[WeatherPoint] = []
        for (lat, lon), location in zip(coordinates, location_payloads):
            hourly = location.get('hourly')
            if not isinstance(hourly, dict):
                raise ProviderError('Open-Meteo did not return hourly weather data.', status_code=502)
            timestamps = hourly.get('time')
            winds = hourly.get('wind_speed_10m')
            rain = hourly.get('rain')
            snow = hourly.get('snowfall')
            if (
                not isinstance(timestamps, list)
                or not timestamps
                or not all(isinstance(values, list) for values in (winds, rain, snow))
                or any(len(values) != len(timestamps) for values in (winds, rain, snow))
            ):
                raise ProviderError('Open-Meteo returned incomplete hourly weather data.', status_code=502)

            for hour_idx, timestamp in enumerate(timestamps):
                if not isinstance(timestamp, str):
                    raise ProviderError('Open-Meteo returned an invalid forecast timestamp.', status_code=502)
                try:
                    sample_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError as exc:
                    raise ProviderError('Open-Meteo returned an invalid forecast timestamp.', status_code=502) from exc
                if sample_dt.tzinfo is None:
                    sample_dt = sample_dt.replace(tzinfo=timezone.utc)
                sample_dt = sample_dt.astimezone(timezone.utc)
                if sample_dt < start_dt or sample_dt > end_dt:
                    continue
                values = (winds[hour_idx], rain[hour_idx], snow[hour_idx])
                if any(value is None for value in values):
                    raise ProviderError('Open-Meteo returned a missing weather value.', status_code=502)
                try:
                    wind_mph, rain_in_hr, snow_in_hr = (float(value) for value in values)
                except (TypeError, ValueError) as exc:
                    raise ProviderError('Open-Meteo returned a non-numeric weather value.', status_code=502) from exc
                if (
                    not all(math.isfinite(value) for value in (wind_mph, rain_in_hr, snow_in_hr))
                    or min(wind_mph, rain_in_hr, snow_in_hr) < 0
                ):
                    raise ProviderError('Open-Meteo returned an invalid weather value.', status_code=502)
                results.append(
                    WeatherPoint(
                        latitude=lat,
                        longitude=lon,
                        timestamp=timestamp,
                        wind_mph=wind_mph,
                        rain_in_hr=rain_in_hr,
                        snow_in_hr=snow_in_hr,
                    )
                )
        return results
