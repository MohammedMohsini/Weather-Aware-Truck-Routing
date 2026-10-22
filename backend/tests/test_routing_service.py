from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import Client

from services.providers.base import GeocodeResult, ProviderError, RouteResult
from services.providers.openroute import OpenRouteProvider
from services.routing_service import generate_3_routes


def test_openroute_provider_requires_key_instead_of_returning_fake_route(monkeypatch):
    monkeypatch.delenv('ORS_API_KEY', raising=False)
    with pytest.raises(ProviderError, match='configure ORS_API_KEY'):
        OpenRouteProvider().route((41.0, -90.0), (39.0, -104.0))


def test_generate_three_routes_uses_via_waypoint_routes_and_deduplicates():
    cache.clear()
    origin = (41.0, -90.0)
    destination = (39.0, -104.0)
    first = RouteResult('ors-route-1', [[41.0, -90.0], [40.0, -97.0], [39.0, -104.0]], 700, 36000, 'Route 1')
    duplicate = RouteResult('route-duplicate', [[41.0, -90.0], [40.0, -97.0], [39.0, -104.0]], 700, 36000, 'Duplicate')
    via_one = RouteResult('ors-route-1', [[41.0, -90.0], [42.0, -97.0], [39.0, -104.0]], 720, 37000, 'Via 1')
    via_two = RouteResult('ors-route-1', [[41.0, -90.0], [38.0, -97.0], [39.0, -104.0]], 730, 38000, 'Via 2')
    provider = type('Provider', (), {
        'route': lambda self, *_args, **_kwargs: [first, duplicate],
        'route_via_waypoint': lambda self, _origin, waypoint, _destination: [via_one if waypoint[0] > 40 else via_two],
    })()

    with patch('services.routing_service.get_routing_provider', return_value=provider):
        routes = generate_3_routes(origin, destination)

    assert len(routes) == 3
    assert [route.route_id for route in routes] == ['route-1', 'route-2', 'route-3']


def test_generate_three_routes_errors_when_provider_cannot_provide_three():
    cache.clear()
    provider = type('Provider', (), {
        'route': lambda self, *_args, **_kwargs: [
            RouteResult('route-1', [[41.0, -90.0], [39.0, -104.0]], 700, 36000, 'Only route'),
        ],
    })()

    with patch('services.routing_service.get_routing_provider', return_value=provider):
        with pytest.raises(ProviderError, match='only 1 distinct'):
            generate_3_routes((41.0, -90.0), (39.0, -104.0))


def test_analyze_endpoint_surfaces_routing_provider_error():
    cache.clear()
    with (
        patch(
            'routing.views.geocode_address',
            side_effect=[
                [GeocodeResult('Chicago', 41.0, -90.0)],
                [GeocodeResult('Denver', 39.0, -104.0)],
            ],
        ),
        patch(
            'routing.views.analyze_routes',
            side_effect=ProviderError('Routing is unavailable: configure ORS_API_KEY.', status_code=503),
        ),
    ):
        response = Client().post(
            '/api/analyze/',
            data={
                'origin': 'Chicago test address',
                'destination': 'Denver test address',
                'departure_time': '2026-01-01T12:00:00Z',
                'load_lb': 45000,
                'interval_miles': 25,
            },
            content_type='application/json',
        )

    assert response.status_code == 503
    assert 'configure ORS_API_KEY' in response.json()['detail']


def test_analyze_endpoint_rejects_nonstandard_checkpoint_interval():
    response = Client().post(
        '/api/analyze/',
        data={
            'origin': 'Chicago',
            'destination': 'Denver',
            'departure_time': '2026-01-01T12:00:00Z',
            'load_lb': 45000,
            'interval_miles': 20,
        },
        content_type='application/json',
    )

    assert response.status_code == 400
    assert 'interval_miles' in response.json()
