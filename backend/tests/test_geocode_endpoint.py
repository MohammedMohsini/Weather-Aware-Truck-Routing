from __future__ import annotations

from django.test import Client


def test_geocode_requires_query():
    client = Client()
    response = client.get('/api/geocode/')
    assert response.status_code == 400
    assert 'q' in response.json()['detail']
