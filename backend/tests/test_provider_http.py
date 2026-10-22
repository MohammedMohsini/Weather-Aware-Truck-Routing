from __future__ import annotations

from unittest.mock import Mock, patch

from services.providers.http_client import request_with_retries


def test_provider_request_retries_transient_server_responses():
    unavailable = Mock(status_code=503)
    recovered = Mock(status_code=200)
    request = Mock(side_effect=[unavailable, recovered])

    with patch('services.providers.http_client.time.sleep'):
        response = request_with_retries(request, 'https://provider.example', timeout=1)

    assert response is recovered
    assert request.call_count == 2
