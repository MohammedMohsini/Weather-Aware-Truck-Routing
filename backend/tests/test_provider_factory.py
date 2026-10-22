from __future__ import annotations

from services.providers.openroute import OpenRouteProvider
from services.providers.osrm import OsrmProvider
from services.provider_factory import get_geocoding_provider, get_routing_provider, get_weather_provider


def test_provider_factory_chooses_no_key_defaults(monkeypatch):
    monkeypatch.delenv('GEOCODING_PROVIDER', raising=False)
    monkeypatch.delenv('ROUTING_PROVIDER', raising=False)
    monkeypatch.delenv('WEATHER_PROVIDER', raising=False)
    assert get_geocoding_provider().__class__.__name__ == 'NominatimProvider'
    assert isinstance(get_routing_provider(), OsrmProvider)
    assert get_weather_provider().__class__.__name__ == 'OpenMeteoProvider'


def test_provider_factory_keeps_openroute_as_an_optional_provider(monkeypatch):
    monkeypatch.setenv('ROUTING_PROVIDER', 'ors')
    assert isinstance(get_routing_provider(), OpenRouteProvider)
