from __future__ import annotations

from typing import Any

from services.providers.base import RouteResult
from services.risk_service import (
    RISK_LEVEL_NAMES,
    calculate_route_metrics,
    recommend_routes,
)
from services.route_service import build_checkpoints
from services.routing_service import generate_3_routes
from services.weather_service import (
    get_weather_for_points,
    index_weather_by_location,
    weather_for_checkpoint,
)


def analyze_routes(
    *,
    origin: tuple[float, float],
    destination: tuple[float, float],
    departure_time: str,
    load_lb: float,
    interval_miles: int,
) -> dict[str, Any]:
    """Evaluate three real driving routes against ETA-matched weather forecasts."""
    routes = generate_3_routes(origin, destination)
    route_checkpoints = [
        build_checkpoints(
            route.geometry,
            interval_miles=interval_miles,
            departure_time=departure_time,
            total_duration_seconds=route.total_duration_seconds,
            total_distance_miles=route.total_distance_miles,
        )
        for route in routes
    ]
    forecast_locations = sorted({
        (round(point.latitude, 4), round(point.longitude, 4))
        for checkpoints in route_checkpoints
        for point in checkpoints
    })
    weather_points = get_weather_for_points(forecast_locations, start_time=departure_time, hours=48)
    weather_index = index_weather_by_location(weather_points)

    evaluated_routes = []
    route_metrics = []
    for route, checkpoints in zip(routes, route_checkpoints):
        checkpoint_data = []
        for checkpoint in checkpoints:
            if checkpoint.eta_utc is None:
                raise ValueError(f'Unable to calculate ETA for checkpoint {checkpoint.index}.')
            weather = weather_for_checkpoint(
                weather_index,
                checkpoint.eta_utc,
                latitude=checkpoint.latitude,
                longitude=checkpoint.longitude,
            )
            if weather is None:
                raise ValueError(
                    f'No weather forecast is available for checkpoint {checkpoint.index} '
                    f'at {checkpoint.eta_utc.isoformat()}. Choose a departure within the forecast window.'
                )
            checkpoint_data.append({
                'index': checkpoint.index,
                'latitude': checkpoint.latitude,
                'longitude': checkpoint.longitude,
                'distance_from_start_miles': checkpoint.distance_from_start_miles,
                'segment_length_miles': checkpoint.segment_length_miles,
                'eta_utc': checkpoint.eta_utc.isoformat(),
                'wind_mph': weather.wind_mph,
                'rain_in_hr': weather.rain_in_hr,
                'snow_in_hr': weather.snow_in_hr,
            })

        metrics = calculate_route_metrics(
            route_id=route.route_id,
            checkpoints=checkpoint_data,
            total_duration_seconds=route.total_duration_seconds,
            total_distance_miles=route.total_distance_miles,
            load_lb=load_lb,
        )
        route_metrics.append(metrics)
        evaluated_routes.append((route, checkpoint_data, metrics))

    recommendation, explanation = recommend_routes(route_metrics)
    result_routes = [
        _serialize_route(route, checkpoints, metrics, recommendation.route_id, explanation)
        for route, checkpoints, metrics in evaluated_routes
    ]
    return {
        'routes': result_routes,
        'recommended_route_id': recommendation.route_id,
        'recommendation_explanation': explanation,
    }


def _serialize_route(
    route: RouteResult,
    checkpoints: list[dict[str, Any]],
    metrics: Any,
    recommended_route_id: str,
    explanation: str,
) -> dict[str, Any]:
    risks_by_index = {risk.index: risk for risk in metrics.checkpoint_risks}
    serialized_checkpoints = []
    for checkpoint in checkpoints:
        risk = risks_by_index[checkpoint['index']]
        serialized_checkpoints.append({
            **checkpoint,
            'condition_levels': {
                condition: {'level': level, 'name': RISK_LEVEL_NAMES[level]}
                for condition, level in risk.condition_levels.items()
            },
            'base_risk': risk.base_risk,
            'base_risk_name': RISK_LEVEL_NAMES[risk.base_risk],
            'risk_level': risk.final_risk,
            'risk': risk.level_name,
            'reason': risk.reason,
        })

    return {
        'route_id': route.route_id,
        'geometry': route.geometry,
        'total_distance_miles': route.total_distance_miles,
        'total_duration_seconds': route.total_duration_seconds,
        'summary': route.summary,
        'checkpoints': serialized_checkpoints,
        'recommended': route.route_id == recommended_route_id,
        'recommendation_explanation': explanation if route.route_id == recommended_route_id else None,
        'metrics': {
            'no_travel_miles': metrics.no_travel_miles,
            'severe_miles': metrics.severe_miles,
            'high_miles': metrics.high_miles,
            'average_risk': metrics.average_risk,
            'total_duration_seconds': metrics.total_duration_seconds,
            'total_distance_miles': metrics.total_distance_miles,
            'miles_by_level': metrics.miles_by_level,
        },
    }
