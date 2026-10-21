from __future__ import annotations

from datetime import datetime, timezone

from services.route_service import (
    build_checkpoints,
    calculate_eta_for_distance,
    decode_polyline,
    haversine_miles,
    route_distance_miles,
)


def test_haversine_distance_is_reasonable():
    start = (40.7128, -74.0060)
    end = (34.0522, -118.2437)
    distance = haversine_miles(start, end)
    assert 2200 < distance < 2800


def test_decode_polyline_returns_points():
    encoded = '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
    points = decode_polyline(encoded)
    assert len(points) > 0
    assert isinstance(points[0], tuple)


def test_calculate_eta_for_distance_uses_proportional_timing():
    departure = '2025-01-01T12:00:00Z'
    eta = calculate_eta_for_distance(departure, 3600, 1800, 3600)
    assert eta == datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc)


def test_build_checkpoints_includes_endpoints_and_interval_points():
    route = [(0.0, 0.0), (0.05, 0.0), (0.10, 0.0)]
    checkpoints = build_checkpoints(route, interval_miles=25, departure_time='2025-01-01T00:00:00Z', total_duration_seconds=3600)
    assert checkpoints[0].distance_from_start_miles == 0.0
    assert checkpoints[-1].latitude == route[-1][0]
    assert checkpoints[-1].longitude == route[-1][1]
    assert len(checkpoints) >= 2


def test_route_distance_miles_sums_segments():
    route = [(0.0, 0.0), (0.01, 0.0), (0.02, 0.0)]
    total = route_distance_miles(route)
    assert total > 0
