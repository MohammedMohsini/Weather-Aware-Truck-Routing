from __future__ import annotations

import pytest

from services.risk_service import (
    RouteMetrics,
    calculate_route_metrics,
    classify_checkpoint,
    classify_weather_condition,
    recommend_routes,
)


def test_wind_threshold_boundaries():
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=24.9, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 0
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=25.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 1
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=34.9, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 1
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=35.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 2
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=44.9, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 2
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=45.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 3
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=54.9, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 3
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=55.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=1000).final_risk == 4


def test_rain_and_snow_threshold_boundaries():
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.09, snow_in_hr=0.0, load_lb=1000).final_risk == 0
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.10, snow_in_hr=0.0, load_lb=1000).final_risk == 1
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.25, snow_in_hr=0.0, load_lb=1000).final_risk == 2
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.50, snow_in_hr=0.0, load_lb=1000).final_risk == 3
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=1.01, snow_in_hr=0.0, load_lb=1000).final_risk == 4

    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.0, snow_in_hr=0.49, load_lb=1000).final_risk == 0
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.0, snow_in_hr=0.50, load_lb=1000).final_risk == 1
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.0, snow_in_hr=1.00, load_lb=1000).final_risk == 2
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.0, snow_in_hr=2.00, load_lb=1000).final_risk == 3
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=5.0, rain_in_hr=0.0, snow_in_hr=3.01, load_lb=1000).final_risk == 4


def test_load_rule_escalations():
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=45.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=30001).final_risk == 4
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=35.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=40001).final_risk == 3
    assert classify_checkpoint(index=0, latitude=0.0, longitude=0.0, wind_mph=55.0, rain_in_hr=0.0, snow_in_hr=0.0, load_lb=20000).final_risk == 4


def test_condition_threshold_edges_are_lower_bound_inclusive():
    expected = {
        'wind': [(24.999, 0), (25, 1), (34.999, 1), (35, 2), (44.999, 2), (45, 3), (54.999, 3), (55, 4)],
        'rain': [(0.0999, 0), (0.10, 1), (0.2499, 1), (0.25, 2), (0.4999, 2), (0.50, 3), (1.00, 3), (1.0001, 4)],
        'snow': [(0.4999, 0), (0.5, 1), (0.9999, 1), (1.0, 2), (1.9999, 2), (2.0, 3), (3.0, 3), (3.0001, 4)],
    }

    for condition, boundaries in expected.items():
        for value, expected_level in boundaries:
            level, _ = classify_weather_condition(condition, value)
            assert level == expected_level, f'{condition}={value} should classify as level {expected_level}'


def test_load_rule_exact_weight_and_decimal_wind_edges():
    def risk(wind_mph: float, load_lb: float) -> int:
        return classify_checkpoint(
            index=0,
            latitude=0.0,
            longitude=0.0,
            wind_mph=wind_mph,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            load_lb=load_lb,
        ).final_risk

    assert risk(45.0, 30000) == 3
    assert risk(45.0, 30001) == 4
    assert risk(54.999, 30001) == 4
    assert risk(55.0, 30000) == 4
    assert risk(35.0, 40000) == 2
    assert risk(35.0, 40001) == 3
    assert risk(44.999, 40001) == 3


def test_load_escalation_never_reduces_more_severe_weather_risk():
    result = classify_checkpoint(
        index=0,
        latitude=0.0,
        longitude=0.0,
        wind_mph=35.0,
        rain_in_hr=1.01,
        snow_in_hr=0.0,
        load_lb=40001,
    )

    assert result.base_risk == 4
    assert result.final_risk == 4
    assert result.reason == 'rain condition is No Travel.'


def test_calculate_route_metrics_uses_segment_length():
    metrics = calculate_route_metrics(
        route_id='route-1',
        checkpoints=[
            {'index': 0, 'latitude': 0.0, 'longitude': 0.0, 'segment_length_miles': 0.0, 'wind_mph': 5.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
            {'index': 1, 'latitude': 1.0, 'longitude': 0.0, 'segment_length_miles': 10.0, 'wind_mph': 50.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
            {'index': 2, 'latitude': 2.0, 'longitude': 0.0, 'segment_length_miles': 5.0, 'wind_mph': 30.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
        ],
        total_duration_seconds=3600,
        total_distance_miles=15.0,
        load_lb=1000,
    )
    assert metrics.miles_by_level['Severe'] == 10.0
    assert metrics.miles_by_level['Moderate'] == 5.0
    assert metrics.average_risk == pytest.approx((3 * 10 + 1 * 5) / 15)


def test_average_risk_is_distance_weighted_and_changes_for_unequal_segments():
    def evaluate_route(route_id: str, low_miles: float, moderate_miles: float):
        return calculate_route_metrics(
            route_id=route_id,
            checkpoints=[
                {'index': 0, 'latitude': 0.0, 'longitude': 0.0, 'segment_length_miles': 0.0, 'wind_mph': 5.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
                {'index': 1, 'latitude': 1.0, 'longitude': 0.0, 'segment_length_miles': low_miles, 'wind_mph': 5.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
                {'index': 2, 'latitude': 2.0, 'longitude': 0.0, 'segment_length_miles': moderate_miles, 'wind_mph': 30.0, 'rain_in_hr': 0.0, 'snow_in_hr': 0.0},
            ],
            total_duration_seconds=3600,
            total_distance_miles=low_miles + moderate_miles,
            load_lb=1000,
        )

    low_risk_weighted = evaluate_route('low-risk-weighted', 90.0, 10.0)
    moderate_risk_weighted = evaluate_route('moderate-risk-weighted', 10.0, 90.0)

    assert low_risk_weighted.average_risk == pytest.approx(0.1)
    assert moderate_risk_weighted.average_risk == pytest.approx(0.9)
    winner, _ = recommend_routes([moderate_risk_weighted, low_risk_weighted])
    assert winner.route_id == 'low-risk-weighted'


def test_recommend_routes_orders_by_priority():
    routes = [
        RouteMetrics(
            route_id='route-a',
            no_travel_miles=0.0,
            severe_miles=20.0,
            high_miles=5.0,
            average_risk=3.0,
            total_duration_seconds=4800,
            total_distance_miles=100.0,
            miles_by_level={'Low': 40.0, 'Moderate': 20.0, 'High': 5.0, 'Severe': 20.0, 'No Travel': 0.0},
            checkpoint_risks=[],
        ),
        RouteMetrics(
            route_id='route-b',
            no_travel_miles=0.0,
            severe_miles=5.0,
            high_miles=20.0,
            average_risk=2.0,
            total_duration_seconds=3900,
            total_distance_miles=90.0,
            miles_by_level={'Low': 50.0, 'Moderate': 10.0, 'High': 20.0, 'Severe': 5.0, 'No Travel': 0.0},
            checkpoint_risks=[],
        ),
        RouteMetrics(
            route_id='route-c',
            no_travel_miles=2.0,
            severe_miles=0.0,
            high_miles=0.0,
            average_risk=1.0,
            total_duration_seconds=4200,
            total_distance_miles=80.0,
            miles_by_level={'Low': 60.0, 'Moderate': 10.0, 'High': 0.0, 'Severe': 0.0, 'No Travel': 2.0},
            checkpoint_risks=[],
        ),
    ]

    winner, explanation = recommend_routes(routes)
    assert winner.route_id == 'route-b'
    assert 'route-b' in explanation


@pytest.mark.parametrize(
    ('first', 'second', 'expected_winner'),
    [
        ((0, 1, 8, 4.0, 5000), (0, 2, 0, 0.0, 1000), 'first'),
        ((0, 2, 1, 4.0, 5000), (0, 2, 2, 0.0, 1000), 'first'),
        ((0, 2, 2, 1.0, 5000), (0, 2, 2, 2.0, 1000), 'first'),
        ((0, 2, 2, 2.0, 1000), (0, 2, 2, 2.0, 2000), 'first'),
    ],
)
def test_recommendation_uses_each_lexicographic_tie_breaker(first, second, expected_winner):
    def route(route_id, values):
        no_travel, severe, high, average, duration = values
        return RouteMetrics(
            route_id=route_id,
            no_travel_miles=no_travel,
            severe_miles=severe,
            high_miles=high,
            average_risk=average,
            total_duration_seconds=duration,
            total_distance_miles=100,
            miles_by_level={'Low': 0, 'Moderate': 0, 'High': high, 'Severe': severe, 'No Travel': no_travel},
            checkpoint_risks=[],
        )

    winner, _ = recommend_routes([route('first', first), route('second', second)])
    assert winner.route_id == expected_winner
