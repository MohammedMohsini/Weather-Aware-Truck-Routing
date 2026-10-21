from __future__ import annotations

import os

from .providers.base import BaseProvider
from .providers.nominatim import NominatimProvider
from .providers.openroute import OpenRouteProvider
from .providers.weather import OpenMeteoProvider


def get_geocoding_provider() -> BaseProvider:
    """Create the configured geocoding provider."""
    provider_name = os.getenv('GEOCODING_PROVIDER', 'nominatim').lower()
    if provider_name == 'nominatim':
        return NominatimProvider()
    raise ValueError(f'Unsupported geocoding provider: {provider_name}')


def get_routing_provider() -> BaseProvider:
    """Create the configured routing provider."""
    provider_name = os.getenv('ROUTING_PROVIDER', 'ors').lower()
    if provider_name in {'ors', 'openrouteservice'}:
        return OpenRouteProvider()
    raise ValueError(f'Unsupported routing provider: {provider_name}')


def get_weather_provider() -> BaseProvider:
    """Create the configured weather provider."""
    provider_name = os.getenv('WEATHER_PROVIDER', 'open-meteo').lower()
    if provider_name in {'open-meteo', 'openmeteo'}:
        return OpenMeteoProvider()
    raise ValueError(f'Unsupported weather provider: {provider_name}')
