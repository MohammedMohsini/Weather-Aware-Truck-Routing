from __future__ import annotations

import hashlib

from django.core.cache import cache

from .providers.base import GeocodeResult
from .provider_factory import get_geocoding_provider


def geocode_address(query: str, *, limit: int = 5) -> list[GeocodeResult]:
    """Geocode a location query with a cache-backed provider wrapper."""
    cleaned = (query or '').strip()
    if not cleaned:
        raise ValueError('Location query is required.')

    query_hash = hashlib.sha256(cleaned.casefold().encode('utf-8')).hexdigest()[:20]
    cache_key = f'geocode:{query_hash}:{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return [GeocodeResult(**item) for item in cached]

    results = get_geocoding_provider().geocode(cleaned)
    serialized = [
        {'display_name': item.display_name, 'latitude': item.latitude, 'longitude': item.longitude}
        for item in results[:limit]
    ]
    cache.set(cache_key, serialized, timeout=60 * 60 * 24)
    return results[:limit]
