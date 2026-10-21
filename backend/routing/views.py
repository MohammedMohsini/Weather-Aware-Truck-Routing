from __future__ import annotations

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from services.geocoding_service import geocode_address
from services.route_service import build_checkpoints
from services.routing_service import generate_3_routes
from .serializers import AnalyzeRequestSerializer, GeocodeQuerySerializer, HeatmapRequestSerializer


@require_http_methods(['GET'])
def health_check(request):
    """Simple health endpoint for verifying the backend is online."""
    return JsonResponse({'status': 'ok', 'service': 'weather-aware-truck-routing'})


@require_http_methods(['GET'])
def geocode(request):
    """Return a geocoded result list for a search query."""
    serializer = GeocodeQuerySerializer(data={'q': request.GET.get('q', '')})
    if not serializer.is_valid():
        return JsonResponse({'detail': serializer.errors}, status=400)

    try:
        results = geocode_address(serializer.validated_data['q'])
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    except Exception as exc:  # pragma: no cover - provider errors handled by validation layer
        return JsonResponse({'detail': f'Geocoding failed: {exc}'}, status=502)

    return JsonResponse({
        'results': [
            {
                'display_name': item.display_name,
                'latitude': item.latitude,
                'longitude': item.longitude,
            }
            for item in results
        ]
    })


@api_view(['POST'])
def analyze(request):
    """Analyze a route and return weather-aware checks, route metrics, and recommendation."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    origin_text = serializer.validated_data['origin']
    destination_text = serializer.validated_data['destination']
    departure_time = serializer.validated_data['departure_time']
    load_lb = float(serializer.validated_data['load_lb'])
    interval_miles = int(serializer.validated_data['interval_miles'])

    origin_cache_key = f'geocode:{origin_text.lower()}'
    destination_cache_key = f'geocode:{destination_text.lower()}'
    origin_result = cache.get(origin_cache_key)
    destination_result = cache.get(destination_cache_key)

    if not origin_result:
        origin_result = geocode_address(origin_text)[:1]
        cache.set(origin_cache_key, origin_result, timeout=60 * 60 * 24)
    if not destination_result:
        destination_result = geocode_address(destination_text)[:1]
        cache.set(destination_cache_key, destination_result, timeout=60 * 60 * 24)

    if not origin_result or not destination_result:
        return Response({'detail': 'Geocoding failed for the supplied origin or destination.'}, status=status.HTTP_400_BAD_REQUEST)

    origin_coord = (float(origin_result[0].latitude), float(origin_result[0].longitude))
    destination_coord = (float(destination_result[0].latitude), float(destination_result[0].longitude))
    routes = generate_3_routes(origin_coord, destination_coord)

    route_payload = []
    for route_index, route in enumerate(routes):
        checkpoints = build_checkpoints(
            route.geometry,
            interval_miles=interval_miles,
            departure_time=departure_time,
            total_duration_seconds=route.total_duration_seconds,
        )
        route_payload.append({
            'route_id': route.route_id,
            'geometry': route.geometry,
            'total_distance_miles': route.total_distance_miles,
            'total_duration_seconds': route.total_duration_seconds,
            'summary': route.summary,
            'checkpoints': [
                {
                    'index': checkpoint.index,
                    'latitude': checkpoint.latitude,
                    'longitude': checkpoint.longitude,
                    'distance_from_start_miles': checkpoint.distance_from_start_miles,
                    'segment_length_miles': checkpoint.segment_length_miles,
                    'eta_utc': checkpoint.eta_utc.isoformat() if checkpoint.eta_utc else None,
                }
                for checkpoint in checkpoints
            ],
            'recommended': False,
            'load_lb': load_lb,
        })

    return Response({
        'routes': route_payload,
        'recommended_route_id': route_payload[0]['route_id'] if route_payload else None,
    })


@api_view(['POST'])
def heatmap(request):
    """Return a corridor heatmap payload; placeholder for the route-grid analysis pipeline."""
    serializer = HeatmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'points': [],
        'hourly_risk': [],
        'message': 'Heatmap generation is implemented in the next phase.',
    })
