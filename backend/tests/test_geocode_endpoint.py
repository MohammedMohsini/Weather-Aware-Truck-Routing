from __future__ import annotations

from unittest.mock import patch

from django.test import Client

from services.providers.base import ProviderError

def test_geocode_requires_query():
    client = Client()
    response = client.get('/api/geocode/')
    assert response.status_code == 400
    assert 'q' in response.json()['detail']


def test_geocode_reports_provider_failure_as_gateway_error():
    with patch('routing.views.geocode_address', side_effect=ProviderError('Geocoding unavailable.')):
        response = Client().get('/api/geocode/', {'q': 'Chicago, IL'})

    assert response.status_code == 502
    assert response.json()['detail'] == 'Geocoding unavailable.'
