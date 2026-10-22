from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache

from services.providers.base import ProviderError, WeatherPoint
from services.weather_service import (
    get_weather_for_points,
    index_weather_by_location,
    weather_for_checkpoint,
)


def test_weather_service_batches_multiple_locations_with_required_units():
    cache.clear()
    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {
            'hourly': {
                'time': ['2026-01-01T00:00', '2026-01-01T01:00'],
                'wind_speed_10m': [10, 11],
                'rain': [0.1, 0.2],
                'snowfall': [0, 0],
            },
        },
        {
            'hourly': {
                'time': ['2026-01-01T00:00', '2026-01-01T01:00'],
                'wind_speed_10m': [30, 31],
                'rain': [0.3, 0.4],
                'snowfall': [0.5, 0.6],
            },
        },
    ]

    with patch('services.providers.weather.httpx.get', return_value=response) as request:
        samples = get_weather_for_points(
            [(41.0, -90.0), (42.0, -91.0)],
            start_time='2026-01-01T00:00:00Z',
            hours=1,
        )

    assert request.call_count == 1
    params = request.call_args.kwargs['params']
    assert params['latitude'] == '41.0,42.0'
    assert params['longitude'] == '-90.0,-91.0'
    assert params['wind_speed_unit'] == 'mph'
    assert params['precipitation_unit'] == 'inch'
    assert params['timezone'] == 'UTC'
    assert len(samples) == 4
    assert samples[0].wind_mph == 10
    assert samples[2].wind_mph == 30


def test_weather_lookup_matches_coordinate_and_rejects_out_of_range_eta():
    samples = [
        WeatherPoint(41.0, -90.0, '2026-01-01T00:00:00Z', 10, 0, 0),
        WeatherPoint(41.0, -90.0, '2026-01-01T01:00:00Z', 20, 0, 0),
        WeatherPoint(42.0, -91.0, '2026-01-01T00:00:00Z', 50, 0, 0),
    ]
    indexed = index_weather_by_location(samples)
    eta = datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc)

    matched = weather_for_checkpoint(indexed, eta, latitude=41.0, longitude=-90.0)
    outside = weather_for_checkpoint(
        indexed,
        datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
        latitude=41.0,
        longitude=-90.0,
    )
    assert matched is not None and matched.wind_mph == 10
    assert outside is None


def test_weather_service_rejects_incomplete_multi_location_response():
    cache.clear()
    response = Mock()
    response.status_code = 200
    response.json.return_value = [
        {
            'hourly': {
                'time': ['2026-01-01T00:00'],
                'wind_speed_10m': [10],
                'rain': [0],
                'snowfall': [0],
            },
        },
    ]

    with patch('services.providers.weather.httpx.get', return_value=response):
        with pytest.raises(ProviderError, match='different number of locations'):
            get_weather_for_points(
                [(41.0, -90.0), (42.0, -91.0)],
                start_time='2026-01-01T00:00:00Z',
                hours=1,
            )


def test_weather_service_rejects_missing_values_instead_of_scoring_them_as_zero():
    cache.clear()
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        'hourly': {
            'time': ['2026-01-01T00:00'],
            'wind_speed_10m': [None],
            'rain': [0],
            'snowfall': [0],
        },
    }

    with patch('services.providers.weather.httpx.get', return_value=response):
        with pytest.raises(ProviderError, match='missing weather value'):
            get_weather_for_points(
                [(41.0, -90.0)],
                start_time='2026-01-01T00:00:00Z',
                hours=1,
            )
