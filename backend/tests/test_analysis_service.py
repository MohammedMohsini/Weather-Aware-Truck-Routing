from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from services.analysis_service import analyze_routes
from services.providers.base import RouteResult, WeatherPoint


def _routes() -> list[RouteResult]:
    return [
        RouteResult('route-1', [[41.0, -90.0], [41.0, -95.0], [41.0, -100.0]], 500, 7200, 'Northern'),
        RouteResult('route-2', [[41.0, -90.0], [42.0, -95.0], [41.0, -100.0]], 520, 7200, 'Central'),
        RouteResult('route-3', [[41.0, -90.0], [40.0, -95.0], [41.0, -100.0]], 540, 7200, 'Southern'),
    ]


def _weather(points: list[tuple[float, float]], **kwargs) -> list[WeatherPoint]:
    departure = datetime(2026, 1, 1, tzinfo=timezone.utc)
    samples = []
    for latitude, longitude in points:
        wind = 20.0 if latitude > 40.5 else 50.0
        for hour in range(3):
            samples.append(WeatherPoint(
                latitude=latitude,
                longitude=longitude,
                timestamp=(departure + timedelta(hours=hour)).isoformat(),
                wind_mph=wind,
                rain_in_hr=0.12,
                snow_in_hr=0.0,
            ))
    return samples


def test_analyze_routes_returns_weather_risk_metrics_and_recommendation():
    with (
        patch('services.analysis_service.generate_3_routes', return_value=_routes()),
        patch('services.analysis_service.get_weather_for_points', side_effect=_weather) as weather_request,
    ):
        result = analyze_routes(
            origin=(41.0, -90.0),
            destination=(41.0, -100.0),
            departure_time='2026-01-01T00:00:00Z',
            load_lb=45000,
            interval_miles=25,
        )

    assert len(result['routes']) == 3
    assert weather_request.call_count == 1
    assert result['recommended_route_id'] == 'route-1'
    assert result['recommendation_explanation']
    recommended = next(route for route in result['routes'] if route['recommended'])
    assert recommended['metrics']['total_distance_miles'] == 500
    assert recommended['metrics']['total_duration_seconds'] == 7200
    assert sum(recommended['metrics']['miles_by_level'].values()) > 0
    checkpoint = recommended['checkpoints'][1]
    assert checkpoint['wind_mph'] == 20.0
    assert checkpoint['rain_in_hr'] == 0.12
    assert checkpoint['snow_in_hr'] == 0.0
    assert checkpoint['condition_levels']['rain'] == {'level': 1, 'name': 'Moderate'}
    assert checkpoint['risk'] == 'Moderate'
    assert checkpoint['reason']


def test_analyze_routes_rejects_checkpoint_outside_forecast_range():
    routes = _routes()
    routes[0] = RouteResult('route-1', routes[0].geometry, 500, 200 * 3600, 'Northern')
    with (
        patch('services.analysis_service.generate_3_routes', return_value=routes),
        patch('services.analysis_service.get_weather_for_points', side_effect=_weather),
    ):
        try:
            analyze_routes(
                origin=(41.0, -90.0),
                destination=(41.0, -100.0),
                departure_time='2026-01-01T00:00:00Z',
                load_lb=28000,
                interval_miles=50,
            )
        except ValueError as exc:
            assert 'No weather forecast is available' in str(exc)
        else:
            raise AssertionError('Expected out-of-range ETA to fail clearly')
