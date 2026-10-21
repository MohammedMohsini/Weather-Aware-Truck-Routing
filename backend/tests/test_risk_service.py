from __future__ import annotations

from services.risk_service import RouteMetrics, calculate_route_metrics, classify_checkpoint, recommend_routes


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
    assert metrics.average_risk > 0


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
