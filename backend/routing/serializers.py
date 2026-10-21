from __future__ import annotations

from datetime import datetime

from rest_framework import serializers


class GeocodeQuerySerializer(serializers.Serializer):
    q = serializers.CharField(trim_whitespace=True, min_length=2)


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(trim_whitespace=True, min_length=2)
    destination = serializers.CharField(trim_whitespace=True, min_length=2)
    departure_time = serializers.CharField()
    load_lb = serializers.FloatField(min_value=1)
    interval_miles = serializers.IntegerField(min_value=10, max_value=50, required=False, default=25)

    def validate_departure_time(self, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:  # pragma: no cover - validation path is exercised by request parsing
            raise serializers.ValidationError('departure_time must be a valid ISO-8601 timestamp.') from exc
        return value


class HeatmapRequestSerializer(serializers.Serializer):
    analysis_id = serializers.CharField(required=False, allow_blank=True)
    route_geometries = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        required=False,
        allow_empty=True,
    )
    start_time = serializers.CharField(required=False, allow_blank=True)
    hours = serializers.IntegerField(min_value=0, max_value=48, required=False, default=48)

    def validate(self, attrs):
        has_analysis = bool(attrs.get('analysis_id'))
        has_geometries = bool(attrs.get('route_geometries'))
        if not has_analysis and not has_geometries:
            raise serializers.ValidationError('Provide either analysis_id or route_geometries.')
        if attrs.get('start_time') in (None, ''):
            attrs['start_time'] = attrs.get('analysis_id') and '1970-01-01T00:00:00Z'
        return attrs
