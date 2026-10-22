from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GeocodeResult:
    """Structured representation of a geocoding result."""
    display_name: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteResult:
    """Driving route containing geometry and summary metadata."""
    route_id: str
    geometry: list[list[float]]
    total_distance_miles: float
    total_duration_seconds: int
    summary: str


@dataclass(frozen=True)
class WeatherPoint:
    """Weather sample for a specific coordinate and time."""
    latitude: float
    longitude: float
    timestamp: str
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


class GeocodingProvider(ABC):
    """Provider interface for address-to-coordinate lookups."""

    @abstractmethod
    def geocode(self, query: str) -> list[GeocodeResult]:
        """Resolve a user query to one or more geocoded coordinates."""


class RoutingProvider(ABC):
    """Provider interface for driving routes."""

    @abstractmethod
    def route(self, origin: tuple[float, float], destination: tuple[float, float], *, alternatives: bool = True) -> list[RouteResult]:
        """Fetch one or more route alternatives between two coordinates."""


class WeatherProvider(ABC):
    """Provider interface for batched hourly weather forecasts."""

    @abstractmethod
    def weather(self, coordinates: list[tuple[float, float]], *, time_start: str, hours: int) -> list[WeatherPoint]:
        """Fetch hourly weather samples for multiple coordinates."""


class ProviderError(RuntimeError):
    """Raised when a remote provider rejects or fails a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}
