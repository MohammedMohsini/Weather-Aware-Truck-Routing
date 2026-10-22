from __future__ import annotations

from datetime import datetime
import math

from rest_framework import serializers


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(trim_whitespace=True, min_length=2, max_length=200)


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(trim_whitespace=True, min_length=2, max_length=200)
    destination = serializers.CharField(trim_whitespace=True, min_length=2, max_length=200)
    departure_time = serializers.CharField(max_length=64)
    load_lb = serializers.FloatField(min_value=1)
    interval_miles = serializers.ChoiceField(choices=(10, 25, 50), required=False, default=25)

    def validate_departure_time(self, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:  # pragma: no cover - validation path is exercised by request parsing
            raise serializers.ValidationError('departure_time must be a valid ISO-8601 timestamp.') from exc
        return value


class HeatmapRequestSerializer(serializers.Serializer):
    route_geometries = serializers.ListField(
        child=serializers.ListField(
            child=serializers.ListField(
                child=serializers.FloatField(),
                min_length=2,
                max_length=2,
            ),
            min_length=2,
            max_length=20000,
        ),
        min_length=3,
        max_length=3,
    )
    start_time = serializers.CharField(max_length=64)
    load_lb = serializers.FloatField(min_value=1)

    def validate_route_geometries(
        self,
        geometries: list[list[list[float]]],
    ) -> list[list[list[float]]]:
        for route in geometries:
            for latitude, longitude in route:
                if (
                    not math.isfinite(latitude)
                    or not math.isfinite(longitude)
                    or not -90 <= latitude <= 90
                    or not -180 <= longitude <= 180
                ):
                    raise serializers.ValidationError(
                        'Route coordinates must use valid latitude and longitude ranges.'
                    )
        return geometries

    def validate_start_time(self, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise serializers.ValidationError('start_time must be a valid ISO-8601 timestamp.') from exc
        return value
