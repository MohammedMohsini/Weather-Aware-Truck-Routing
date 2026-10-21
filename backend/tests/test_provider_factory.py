from __future__ import annotations

from services.provider_factory import get_geocoding_provider, get_routing_provider, get_weather_provider


def test_provider_factory_chooses_expected_defaults():
    assert get_geocoding_provider().__class__.__name__ == 'NominatimProvider'
    assert get_routing_provider().__class__.__name__ == 'OpenRouteProvider'
    assert get_weather_provider().__class__.__name__ == 'OpenMeteoProvider'
