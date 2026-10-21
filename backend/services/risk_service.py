from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RISK_LEVEL_NAMES = {
    0: 'Low',
    1: 'Moderate',
    2: 'High',
    3: 'Severe',
    4: 'No Travel',
}


def _risk_level_from_value(condition: str, value: float) -> tuple[int, str]:
    """Return the numeric risk level and label for a single condition."""
    if condition == 'wind':
        if value < 25:
            return 0, 'Low'
        if value < 35:
            return 1, 'Moderate'
        if value < 45:
            return 2, 'High'
        if value < 55:
            return 3, 'Severe'
        return 4, 'No Travel'

    if condition == 'rain':
        if value < 0.10:
            return 0, 'Low'
        if value < 0.25:
            return 1, 'Moderate'
        if value < 0.50:
            return 2, 'High'
        if value <= 1.00:
            return 3, 'Severe'
        return 4, 'No Travel'

    if condition == 'snow':
        if value < 0.5:
            return 0, 'Low'
        if value < 1.0:
            return 1, 'Moderate'
        if value < 2.0:
            return 2, 'High'
        if value <= 3.0:
            return 3, 'Severe'
        return 4, 'No Travel'

    raise ValueError(f'Unsupported condition: {condition}')


@dataclass(frozen=True)
class CheckpointRisk:
    """Risk classification data for one route checkpoint."""

    index: int
    latitude: float
    longitude: float
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float
    load_lb: float
    condition_levels: dict[str, int]
    base_risk: int
    final_risk: int
    reason: str

    @property
    def level_name(self) -> str:
        return RISK_LEVEL_NAMES[self.final_risk]


@dataclass(frozen=True)
class RouteMetrics:
    """Aggregate route risk metrics for recommendation."""

    route_id: str
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    average_risk: float
    total_duration_seconds: int | float
    total_distance_miles: float
    miles_by_level: dict[str, float]
    checkpoint_risks: list[CheckpointRisk]


def classify_checkpoint(
    *,
    index: int,
    latitude: float,
    longitude: float,
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_lb: float,
) -> CheckpointRisk:
    """Classify weather for a checkpoint and apply the load-based escalation rules."""
    condition_levels = {
        'wind': _risk_level_from_value('wind', wind_mph)[0],
        'rain': _risk_level_from_value('rain', rain_in_hr)[0],
        'snow': _risk_level_from_value('snow', snow_in_hr)[0],
    }
    base_risk = max(condition_levels.values())
    base_reason = (
        'wind' if condition_levels['wind'] == base_risk else
        'rain' if condition_levels['rain'] == base_risk else
        'snow'
    )

    final_risk = base_risk
    final_reason = f'{base_reason} condition is {RISK_LEVEL_NAMES[base_risk]}.'

    if wind_mph >= 55:
        final_risk = 4
        final_reason = 'Wind >= 55 mph means no travel for any load.'
    elif 45 <= wind_mph <= 54 and load_lb > 30000:
        final_risk = 4
        final_reason = 'Wind 45-54 mph with load over 30,000 lb means no travel.'
    elif 35 <= wind_mph <= 44 and load_lb > 40000:
        final_risk = 3
        final_reason = 'Wind 35-44 mph with load over 40,000 lb escalates to Severe.'

    return CheckpointRisk(
        index=index,
        latitude=latitude,
        longitude=longitude,
        wind_mph=wind_mph,
        rain_in_hr=rain_in_hr,
        snow_in_hr=snow_in_hr,
        load_lb=load_lb,
        condition_levels=condition_levels,
        base_risk=base_risk,
        final_risk=final_risk,
        reason=final_reason,
    )


def classify_weather_condition(condition: str, value: float) -> tuple[int, str]:
    """Public alias for the condition-to-risk classification helper."""
    return _risk_level_from_value(condition, value)


def calculate_route_metrics(
    *,
    route_id: str,
    checkpoints: list[dict[str, Any]],
    total_duration_seconds: int | float,
    total_distance_miles: float,
    load_lb: float,
) -> RouteMetrics:
    """Aggregate all route metrics for recommendation and UI rendering."""
    miles_by_level = {name: 0.0 for name in ['Low', 'Moderate', 'High', 'Severe', 'No Travel']}
    checkpoint_risks: list[CheckpointRisk] = []
    risk_values: list[int] = []

    for checkpoint in checkpoints:
        risk = classify_checkpoint(
            index=checkpoint.get('index', 0),
            latitude=float(checkpoint['latitude']),
            longitude=float(checkpoint['longitude']),
            wind_mph=float(checkpoint.get('wind_mph', 0.0)),
            rain_in_hr=float(checkpoint.get('rain_in_hr', 0.0)),
            snow_in_hr=float(checkpoint.get('snow_in_hr', 0.0)),
            load_lb=float(load_lb),
        )
        checkpoint_risks.append(risk)
        risk_values.append(risk.final_risk)

        segment_length = float(checkpoint.get('segment_length_miles', 0.0))
        if segment_length > 0:
            miles_by_level[RISK_LEVEL_NAMES[risk.final_risk]] += segment_length

    average_risk = sum(risk_values) / len(risk_values) if risk_values else 0.0
    return RouteMetrics(
        route_id=route_id,
        no_travel_miles=miles_by_level['No Travel'],
        severe_miles=miles_by_level['Severe'],
        high_miles=miles_by_level['High'],
        average_risk=average_risk,
        total_duration_seconds=total_duration_seconds,
        total_distance_miles=total_distance_miles,
        miles_by_level=miles_by_level,
        checkpoint_risks=checkpoint_risks,
    )


def recommend_routes(route_evaluations: list[RouteMetrics]) -> tuple[RouteMetrics, str]:
    """Select the best route using the assignment-specified ranking."""
    if not route_evaluations:
        raise ValueError('At least one route evaluation is required.')

    ordered = sorted(
        route_evaluations,
        key=lambda route: (
            route.no_travel_miles,
            route.severe_miles,
            route.high_miles,
            route.average_risk,
            route.total_duration_seconds,
        ),
    )
    best = ordered[0]

    compare_lines = []
    for route in ordered[1:]:
        compare_lines.append(
            f"{route.route_id}: {route.no_travel_miles:.1f} no-travel mi, {route.severe_miles:.1f} severe mi, {route.high_miles:.1f} high mi"
        )

    comparison = '; '.join(compare_lines) if compare_lines else 'This is the only route available.'
    explanation = (
        f"{best.route_id} wins because it has the lowest no-travel miles ({best.no_travel_miles:.1f}), "
        f"then the fewest severe miles ({best.severe_miles:.1f}), then the fewest high miles ({best.high_miles:.1f}), "
        f"with average risk {best.average_risk:.2f} and travel time {best.total_duration_seconds:.0f}s. "
        f"Comparison: {comparison}"
    )
    return best, explanation


summarize_route_metrics = calculate_route_metrics
rank_routes = recommend_routes
classify_risk = classify_checkpoint
