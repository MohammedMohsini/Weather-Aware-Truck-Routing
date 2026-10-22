from __future__ import annotations

import httpx

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.request import Request

from services.geocoding_service import geocode_address
from services.analysis_service import analyze_routes
from services.providers.base import ProviderError
from services.heatmap_service import generate_heatmap
from .serializers import AnalyzeRequestSerializer, GeocodeQuerySerializer, HeatmapRequestSerializer


@require_http_methods(['GET'])
def health_check(request: HttpRequest) -> JsonResponse:
    """Simple health endpoint for verifying the backend is online."""
    return JsonResponse({'status': 'ok', 'service': 'weather-aware-truck-routing'})


@require_http_methods(['GET'])
def geocode(request: HttpRequest) -> JsonResponse:
    """Return a geocoded result list for a search query."""
    serializer = GeocodeQuerySerializer(data={'q': request.GET.get('q', '')})
    if not serializer.is_valid():
        return JsonResponse({'detail': serializer.errors}, status=400)

    try:
        results = geocode_address(serializer.validated_data['q'])
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    except ProviderError as exc:
        response_status = (
            exc.status_code
            if exc.status_code and 400 <= exc.status_code < 600
            else status.HTTP_502_BAD_GATEWAY
        )
        return JsonResponse({'detail': str(exc)}, status=response_status)
    except httpx.RequestError:
        return JsonResponse(
            {'detail': 'The geocoding provider could not be reached. Please try again later.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

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
def analyze(request: Request) -> Response:
    """Analyze a route and return weather-aware checks, route metrics, and recommendation."""
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    origin_text = serializer.validated_data['origin']
    destination_text = serializer.validated_data['destination']
    departure_time = serializer.validated_data['departure_time']
    load_lb = float(serializer.validated_data['load_lb'])
    interval_miles = int(serializer.validated_data['interval_miles'])

    try:
        origin_result = geocode_address(origin_text)[:1]
        destination_result = geocode_address(destination_text)[:1]
        if not origin_result or not destination_result:
            return Response(
                {'detail': 'Geocoding failed for the supplied origin or destination.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        origin_coord = (float(origin_result[0].latitude), float(origin_result[0].longitude))
        destination_coord = (float(destination_result[0].latitude), float(destination_result[0].longitude))
        result = analyze_routes(
            origin=origin_coord,
            destination=destination_coord,
            departure_time=departure_time,
            load_lb=load_lb,
            interval_miles=interval_miles,
        )
    except ProviderError as exc:
        response_status = (
            exc.status_code
            if exc.status_code and 400 <= exc.status_code < 600
            else status.HTTP_502_BAD_GATEWAY
        )
        return Response({'detail': str(exc)}, status=response_status)
    except httpx.RequestError:
        return Response(
            {'detail': 'The geocoding, routing, or weather provider could not be reached. Please try again later.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response(result)


@api_view(['POST'])
def heatmap(request: Request) -> Response:
    """Return real hourly weather-risk samples along the submitted route corridor."""
    serializer = HeatmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = generate_heatmap(
            route_geometries=serializer.validated_data['route_geometries'],
            start_time=serializer.validated_data['start_time'],
            load_lb=float(serializer.validated_data['load_lb']),
        )
    except ProviderError as exc:
        response_status = (
            exc.status_code
            if exc.status_code and 400 <= exc.status_code < 600
            else status.HTTP_502_BAD_GATEWAY
        )
        return Response({'detail': str(exc)}, status=response_status)
    except httpx.RequestError:
        return Response(
            {'detail': 'The weather provider could not be reached. Please try again later.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    return Response(result)
