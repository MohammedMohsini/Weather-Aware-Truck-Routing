from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class Checkpoint:
    """A route checkpoint with cumulative distance and ETA information."""

    index: int
    latitude: float
    longitude: float
    distance_from_start_miles: float
    segment_length_miles: float
    eta_utc: datetime | None


def haversine_miles(start: tuple[float, float], end: tuple[float, float]) -> float:
    """Distance between two lat/lng coordinates in miles."""
    lat1, lon1 = map(math.radians, start)
    lat2, lon2 = map(math.radians, end)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * 3958.8 * math.asin(math.sqrt(a))


def interpolate_point(start: tuple[float, float], end: tuple[float, float], ratio: float) -> tuple[float, float]:
    """Interpolate between two lat/lng points by a ratio between 0 and 1."""
    return (
        start[0] + (end[0] - start[0]) * ratio,
        start[1] + (end[1] - start[1]) * ratio,
    )


def normalize_datetime(value: str | datetime | None) -> datetime | None:
    """Return a timezone-aware UTC datetime from a string or datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_eta_for_distance(
    departure_time: str | datetime | None,
    total_duration_seconds: int | float | None,
    distance_from_start_miles: float,
    total_distance_miles: float,
) -> datetime | None:
    """ETA for a checkpoint using proportional distance along the route.

    When only overall route duration is available, we estimate checkpoint ETAs by
    interpolating linearly by distance traveled, which matches the route-level
    timing information used by the assignment.
    """
    if total_distance_miles <= 0:
        return normalize_datetime(departure_time)
    departure = normalize_datetime(departure_time)
    if departure is None or total_duration_seconds is None:
        return None
    ratio = distance_from_start_miles / total_distance_miles
    seconds_offset = float(total_duration_seconds) * ratio
    return departure + timedelta(seconds=seconds_offset)


def build_checkpoints(
    route_geometry: list[tuple[float, float]] | list[list[float]],
    *,
    interval_miles: int | float,
    departure_time: str | datetime | None = None,
    total_duration_seconds: int | float | None = None,
    total_distance_miles: float | None = None,
) -> list[Checkpoint]:
    """Create route checkpoints at the requested interval and the route endpoints.

    Each checkpoint stores the distance from the route start and the segment length
    from the previous checkpoint. This makes downstream risk aggregation consistent
    with the assignment requirement that each segment contributes its own mileage.
    """
    if not route_geometry:
        return []

    normalized_route = [(float(lat), float(lng)) for lat, lng in route_geometry]
    if len(normalized_route) == 1:
        eta = calculate_eta_for_distance(departure_time, total_duration_seconds, 0.0, 0.0)
        return [Checkpoint(0, normalized_route[0][0], normalized_route[0][1], 0.0, 0.0, eta)]

    cumulative = [0.0]
    for i in range(1, len(normalized_route)):
        cumulative.append(cumulative[-1] + haversine_miles(normalized_route[i - 1], normalized_route[i]))

    geometry_distance_miles = cumulative[-1]
    if total_distance_miles is not None and total_distance_miles > 0 and geometry_distance_miles > 0:
        distance_scale = total_distance_miles / geometry_distance_miles
        cumulative = [distance * distance_scale for distance in cumulative]
    total_route_distance_miles = cumulative[-1]
    interval = (
        float(interval_miles)
        if interval_miles and interval_miles > 0
        else max(total_route_distance_miles, 1.0)
    )

    checkpoints: list[Checkpoint] = []
    current_checkpoint_index = 0
    previous_distance = 0.0

    def add_checkpoint_at(distance: float, point: tuple[float, float], segment_length: float) -> None:
        nonlocal current_checkpoint_index, previous_distance
        eta = calculate_eta_for_distance(
            departure_time,
            total_duration_seconds,
            distance,
            total_route_distance_miles,
        )
        checkpoints.append(
            Checkpoint(
                index=current_checkpoint_index,
                latitude=point[0],
                longitude=point[1],
                distance_from_start_miles=distance,
                segment_length_miles=segment_length,
                eta_utc=eta,
            )
        )
        current_checkpoint_index += 1
        previous_distance = distance

    add_checkpoint_at(0.0, normalized_route[0], 0.0)

    if total_route_distance_miles > 0:
        target = interval
        while target < total_route_distance_miles:
            segment_index = 0
            while segment_index < len(normalized_route) - 1:
                start_dist = cumulative[segment_index]
                end_dist = cumulative[segment_index + 1]
                if start_dist <= target <= end_dist:
                    local_ratio = (target - start_dist) / max(end_dist - start_dist, 1e-9)
                    point = interpolate_point(normalized_route[segment_index], normalized_route[segment_index + 1], local_ratio)
                    segment_length = target - previous_distance
                    add_checkpoint_at(target, point, segment_length)
                    break
                segment_index += 1
            target += interval

    end_distance = total_route_distance_miles
    end_point = normalized_route[-1]
    end_segment = end_distance - previous_distance if checkpoints else end_distance
    if not (checkpoints and checkpoints[-1].distance_from_start_miles == end_distance):
        add_checkpoint_at(end_distance, end_point, end_segment)

    # Remove any exact duplicate if a route naturally makes the final point identical to the last interval checkpoint.
    deduped: list[Checkpoint] = []
    for checkpoint in checkpoints:
        if deduped and checkpoint.distance_from_start_miles == deduped[-1].distance_from_start_miles:
            continue
        deduped.append(checkpoint)
    return deduped


def route_distance_miles(route_geometry: list[tuple[float, float]] | list[list[float]]) -> float:
    """Compute a route's length by summing segment distances in miles."""
    if len(route_geometry) < 2:
        return 0.0
    total = 0.0
    for previous, current in zip(route_geometry, route_geometry[1:]):
        total += haversine_miles((float(previous[0]), float(previous[1])), (float(current[0]), float(current[1])))
    return total
