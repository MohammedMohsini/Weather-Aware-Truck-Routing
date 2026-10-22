from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import Client

from services.providers.base import WeatherPoint
from services.heatmap_service import generate_heatmap


def _weather(points, **kwargs):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        WeatherPoint(
            latitude=latitude,
            longitude=longitude,
            timestamp=(start + timedelta(hours=hour)).isoformat(),
            wind_mph=50.0,
            rain_in_hr=0.1,
            snow_in_hr=0.0,
        )
        for latitude, longitude in points
        for hour in range(49)
    ]


def _route_geometries():
    return [
        [[41.0, -90.0], [41.0, -92.0], [41.0, -94.0]],
        [[41.5, -90.0], [42.0, -92.0], [42.5, -94.0]],
        [[40.5, -90.0], [40.0, -92.0], [39.5, -94.0]],
    ]


def test_heatmap_contains_batched_real_weather_risk_for_hours_zero_through_48():
    with patch('services.heatmap_service.get_weather_for_points', side_effect=_weather) as weather_request:
        result = generate_heatmap(
            route_geometries=_route_geometries(),
            start_time='2026-01-01T00:00:00Z',
            load_lb=45000,
        )

    assert weather_request.call_count == 1
    assert 0 < len(result['points']) <= 300
    assert len(result['hours']) == 49
    assert result['hours'][0]['hour'] == 0
    assert result['hours'][-1]['hour'] == 48
    assert len(result['points'][0]['hourly']) == 49
    assert result['points'][0]['hourly'][0]['risk'] == 'No Travel'
    assert result['points'][0]['hourly'][0]['wind_mph'] == 50.0


def test_heatmap_endpoint_returns_hourly_risk_payload():
    payload = {
        'hours': [{'hour': 0, 'timestamp_utc': '2026-01-01T00:00:00+00:00'}],
        'points': [{'latitude': 41.0, 'longitude': -90.0, 'route_ids': ['route-1'], 'hourly': []}],
        'forecast_hours': 48,
        'load_lb': 28000,
    }
    with patch('routing.views.generate_heatmap', return_value=payload):
        response = Client().post(
            '/api/heatmap/',
            data={
                'route_geometries': _route_geometries(),
                'start_time': '2026-01-01T00:00:00Z',
                'load_lb': 28000,
            },
            content_type='application/json',
        )

    assert response.status_code == 200
    assert response.json()['forecast_hours'] == 48
    assert response.json()['hours'][0]['hour'] == 0


def test_heatmap_endpoint_rejects_out_of_range_coordinates():
    response = Client().post(
        '/api/heatmap/',
        data={
            'route_geometries': [
                [[91.0, -90.0], [41.0, -92.0]],
                [[41.5, -90.0], [42.0, -92.0]],
                [[40.5, -90.0], [40.0, -92.0]],
            ],
            'start_time': '2026-01-01T00:00:00Z',
            'load_lb': 28000,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'route_geometries' in response.json()
