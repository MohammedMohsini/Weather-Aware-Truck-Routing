from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from services.providers.base import ProviderError
from services.providers.osrm import METERS_PER_MILE, OsrmProvider


def _osrm_response():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        'code': 'Ok',
        'routes': [
            {
                'distance': 160934.4,
                'duration': 3600,
                'geometry': {'coordinates': [[-87.6, 41.8], [-95.0, 40.0], [-104.9, 39.7]]},
            }
        ],
    }
    return response


def test_osrm_provider_converts_coordinates_and_distance_units():
    with patch('services.providers.osrm.request_with_retries', return_value=_osrm_response()) as request:
        routes = OsrmProvider().route((41.8, -87.6), (39.7, -104.9))

    assert len(routes) == 1
    assert routes[0].geometry == [[41.8, -87.6], [40.0, -95.0], [39.7, -104.9]]
    assert routes[0].total_distance_miles == pytest.approx(100)
    assert routes[0].total_duration_seconds == 3600
    assert request.call_args.args[1].endswith('-87.6,41.8;-104.9,39.7')
    assert request.call_args.kwargs['params']['alternatives'] == '3'


def test_osrm_via_waypoint_sends_all_three_coordinates():
    with patch('services.providers.osrm.request_with_retries', return_value=_osrm_response()) as request:
        OsrmProvider().route_via_waypoint((41.8, -87.6), (40.0, -95.0), (39.7, -104.9))

    assert request.call_args.args[1].endswith('-87.6,41.8;-95.0,40.0;-104.9,39.7')
    assert request.call_args.kwargs['params']['alternatives'] == 'false'


def test_osrm_provider_reports_provider_errors():
    response = _osrm_response()
    response.status_code = 429
    with patch('services.providers.osrm.request_with_retries', return_value=response):
        with pytest.raises(ProviderError, match='OSRM routing request failed'):
            OsrmProvider().route((41.8, -87.6), (39.7, -104.9))


def test_osrm_provider_rejects_invalid_route_metrics():
    response = _osrm_response()
    response.json.return_value['routes'][0]['distance'] = float('nan')
    with patch('services.providers.osrm.request_with_retries', return_value=response):
        with pytest.raises(ProviderError, match='invalid route metrics'):
            OsrmProvider().route((41.8, -87.6), (39.7, -104.9))
