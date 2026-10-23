from __future__ import annotations

from datetime import datetime, timezone

from services.route_service import (
    build_checkpoints,
    calculate_eta_for_distance,
    haversine_miles,
    route_distance_miles,
)


def test_haversine_distance_is_reasonable():
    start = (40.7128, -74.0060)
    end = (34.0522, -118.2437)
    distance = haversine_miles(start, end)
    assert 2200 < distance < 2800


def test_calculate_eta_for_distance_uses_proportional_timing():
    departure = '2025-01-01T12:00:00Z'
    eta = calculate_eta_for_distance(departure, 3600, 1800, 3600)
    assert eta == datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc)


def test_checkpoint_etas_increase_along_route():
    route = [(0.0, 0.0), (0.0, 3.0)]
    checkpoints = build_checkpoints(
        route,
        interval_miles=25,
        departure_time='2025-01-01T12:00:00Z',
        total_duration_seconds=6 * 60 * 60,
    )

    etas = [checkpoint.eta_utc for checkpoint in checkpoints]
    assert all(eta is not None for eta in etas)
    assert all(later > earlier for earlier, later in zip(etas, etas[1:]))


def test_build_checkpoints_includes_endpoints_and_interval_points():
    route = [(0.0, 0.0), (0.05, 0.0), (0.10, 0.0)]
    checkpoints = build_checkpoints(route, interval_miles=25, departure_time='2025-01-01T00:00:00Z', total_duration_seconds=3600)
    assert checkpoints[0].distance_from_start_miles == 0.0
    assert checkpoints[-1].latitude == route[-1][0]
    assert checkpoints[-1].longitude == route[-1][1]
    assert len(checkpoints) >= 2


def test_checkpoint_generation_respects_supported_intervals_and_endpoints():
    route = [(0.0, 0.0), (0.0, 3.0)]
    for interval in (10, 25, 50):
        checkpoints = build_checkpoints(
            route,
            interval_miles=interval,
            departure_time='2025-01-01T00:00:00Z',
            total_duration_seconds=3600,
        )
        distances = [checkpoint.distance_from_start_miles for checkpoint in checkpoints]

        assert distances[0] == 0
        assert (checkpoints[-1].latitude, checkpoints[-1].longitude) == route[-1]
        assert distances[-1] > 0
        assert all(abs(distance / interval - round(distance / interval)) < 1e-8 for distance in distances[1:-1])
        assert abs(sum(checkpoint.segment_length_miles for checkpoint in checkpoints) - distances[-1]) < 1e-8


def test_checkpoints_use_provider_distance_for_spacing_and_segment_totals():
    route = [(0.0, 0.0), (0.0, 3.0)]
    checkpoints = build_checkpoints(
        route,
        interval_miles=25,
        total_distance_miles=250,
        departure_time='2025-01-01T00:00:00Z',
        total_duration_seconds=3600,
    )

    distances = [checkpoint.distance_from_start_miles for checkpoint in checkpoints]
    assert distances == [0, 25, 50, 75, 100, 125, 150, 175, 200, 225, 250]
    assert sum(checkpoint.segment_length_miles for checkpoint in checkpoints) == 250
    assert checkpoints[-1].distance_from_start_miles == 250


def test_route_distance_miles_sums_segments():
    route = [(0.0, 0.0), (0.01, 0.0), (0.02, 0.0)]
    total = route_distance_miles(route)
    assert total > 0
