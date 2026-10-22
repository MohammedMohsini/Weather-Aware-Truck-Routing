import type { Checkpoint, RiskLevel, RoutePoint, RouteSummary } from '../types/route';

export type AnalyzePayload = {
  origin: string;
  destination: string;
  departure_time: string;
  load_lb: number;
  interval_miles: number;
};

export type HeatmapPayload = {
  route_geometries: number[][][];
  start_time: string;
  load_lb: number;
};

export type HeatmapResponse = {
  hours: { hour: number; timestamp_utc: string }[];
  points: {
    latitude: number;
    longitude: number;
    route_ids: string[];
    hourly: { risk_level: number }[];
  }[];
  forecast_hours: number;
  load_lb: number;
};

export type PlaceResult = {
  display_name: string;
  latitude: number;
  longitude: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
const geocodeCache = new Map<string, PlaceResult[]>();

async function readApiError(response: Response, fallback: string): Promise<Error> {
  const body: unknown = await response.json().catch(() => null);
  if (isRecord(body) && 'detail' in body) {
    const detail = body.detail;
    if (typeof detail === 'string') {
      return new Error(detail);
    }
    if (isRecord(detail)) {
      const firstError = Object.values(detail)[0];
      if (Array.isArray(firstError) && typeof firstError[0] === 'string') {
        return new Error(firstError[0]);
      }
      return new Error(JSON.stringify(detail));
    }
  }
  return new Error(`${fallback} (${response.status}).`);
}

export async function pingApi(): Promise<void> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 8000);
  const response = await fetch(`${API_BASE_URL}/api/health/`, { signal: controller.signal }).finally(() => {
    window.clearTimeout(timeout);
  });
  if (!response.ok) {
    throw new Error(`Backend health check failed (${response.status}).`);
  }
}

export async function geocodePlaces(query: string, signal: AbortSignal): Promise<PlaceResult[]> {
  const cleanedQuery = query.trim();
  const cacheKey = cleanedQuery.toLowerCase();
  const cached = geocodeCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const response = await fetch(`${API_BASE_URL}/api/geocode/?q=${encodeURIComponent(cleanedQuery)}`, {
    signal,
  });
  if (!response.ok) {
    throw await readApiError(response, 'Location search failed');
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload) || !Array.isArray(payload.results)) {
    throw new Error('The geocoding service returned an invalid response.');
  }
  const results = payload.results.map((result: unknown): PlaceResult => {
    if (
      !isRecord(result) ||
      typeof result.display_name !== 'string' ||
      !isFiniteNumber(result.latitude) ||
      !isFiniteNumber(result.longitude) ||
      result.latitude < -90 ||
      result.latitude > 90 ||
      result.longitude < -180 ||
      result.longitude > 180
    ) {
      throw new Error('The geocoding service returned an invalid location.');
    }
    return {
      display_name: result.display_name,
      latitude: result.latitude,
      longitude: result.longitude,
    };
  });
  geocodeCache.set(cacheKey, results);
  return results;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isRiskLevel(value: unknown): value is RiskLevel {
  return (
    value === 'Low' || value === 'Moderate' || value === 'High' || value === 'Severe' || value === 'No Travel'
  );
}

function parseCheckpoint(value: unknown): Checkpoint {
  if (
    !isRecord(value) ||
    typeof value.index !== 'number' ||
    !Number.isInteger(value.index) ||
    !isFiniteNumber(value.latitude) ||
    !isFiniteNumber(value.longitude) ||
    !isFiniteNumber(value.distance_from_start_miles) ||
    !isFiniteNumber(value.segment_length_miles) ||
    typeof value.eta_utc !== 'string' ||
    !isFiniteNumber(value.wind_mph) ||
    !isFiniteNumber(value.rain_in_hr) ||
    !isFiniteNumber(value.snow_in_hr) ||
    !isRiskLevel(value.risk) ||
    typeof value.reason !== 'string'
  ) {
    throw new Error('The analysis service returned an incomplete checkpoint forecast.');
  }
  return {
    index: value.index,
    latitude: value.latitude,
    longitude: value.longitude,
    distance_from_start_miles: value.distance_from_start_miles,
    segment_length_miles: value.segment_length_miles,
    eta_utc: value.eta_utc,
    wind_mph: value.wind_mph,
    rain_in_hr: value.rain_in_hr,
    snow_in_hr: value.snow_in_hr,
    risk: value.risk,
    reason: value.reason,
  };
}

function parseGeometry(value: unknown): RoutePoint[] {
  if (!Array.isArray(value) || value.length < 2) {
    throw new Error('The analysis service returned invalid route geometry.');
  }
  return value.map((point): RoutePoint => {
    if (
      !Array.isArray(point) ||
      point.length !== 2 ||
      !isFiniteNumber(point[0]) ||
      !isFiniteNumber(point[1])
    ) {
      throw new Error('The analysis service returned invalid route coordinates.');
    }
    return [point[0], point[1]];
  });
}

function parseMetrics(value: unknown): NonNullable<RouteSummary['metrics']> {
  if (!isRecord(value) || !isRecord(value.miles_by_level)) {
    throw new Error('The analysis service returned incomplete route metrics.');
  }
  const levels: RiskLevel[] = ['Low', 'Moderate', 'High', 'Severe', 'No Travel'];
  const milesByLevel = {} as Record<RiskLevel, number>;
  for (const level of levels) {
    const miles = value.miles_by_level[level];
    if (!isFiniteNumber(miles)) {
      throw new Error('The analysis service returned invalid route metrics.');
    }
    milesByLevel[level] = miles;
  }
  if (
    !isFiniteNumber(value.no_travel_miles) ||
    !isFiniteNumber(value.severe_miles) ||
    !isFiniteNumber(value.high_miles) ||
    !isFiniteNumber(value.average_risk)
  ) {
    throw new Error('The analysis service returned invalid route metrics.');
  }
  return {
    no_travel_miles: value.no_travel_miles,
    severe_miles: value.severe_miles,
    high_miles: value.high_miles,
    average_risk: value.average_risk,
    miles_by_level: milesByLevel,
  };
}

function parseRoute(value: unknown, index: number): RouteSummary {
  if (
    !isRecord(value) ||
    typeof value.route_id !== 'string' ||
    !value.route_id ||
    !isFiniteNumber(value.total_distance_miles) ||
    !isFiniteNumber(value.total_duration_seconds) ||
    typeof value.summary !== 'string' ||
    typeof value.recommended !== 'boolean' ||
    !Array.isArray(value.checkpoints) ||
    value.checkpoints.length < 2 ||
    (value.recommendation_explanation !== null && typeof value.recommendation_explanation !== 'string')
  ) {
    throw new Error(`The analysis service returned incomplete data for route ${index + 1}.`);
  }
  return {
    route_id: value.route_id,
    geometry: parseGeometry(value.geometry),
    total_distance_miles: value.total_distance_miles,
    total_duration_seconds: value.total_duration_seconds,
    summary: value.summary,
    recommended: value.recommended,
    recommendation_explanation: value.recommendation_explanation,
    checkpoints: value.checkpoints.map(parseCheckpoint),
    metrics: parseMetrics(value.metrics),
  };
}

function parseRoutes(payload: unknown): RouteSummary[] {
  if (!isRecord(payload) || !Array.isArray(payload.routes) || payload.routes.length !== 3) {
    throw new Error('The analysis service did not return exactly three analyzed routes.');
  }
  if (
    payload.routes.some(
      (route) =>
        isRecord(route) && typeof route.route_id === 'string' && route.route_id.startsWith('fallback-route-'),
    )
  ) {
    throw new Error(
      'The backend is returning unscored fallback routes. Deploy the latest backend and verify its ORS_API_KEY; these routes cannot be safely analyzed.',
    );
  }
  const routes = payload.routes.map(parseRoute);
  if (
    routes.filter((route) => route.recommended).length !== 1 ||
    new Set(routes.map((route) => route.route_id)).size !== 3
  ) {
    throw new Error('The analysis service returned an invalid route recommendation.');
  }
  return routes;
}

export async function analyzeRoutes(payload: AnalyzePayload): Promise<RouteSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/analyze/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await readApiError(response, 'Routing analysis failed');
  }

  const data: unknown = await response.json();
  return parseRoutes(data);
}

function parseHeatmapResponse(value: unknown): HeatmapResponse {
  if (
    !isRecord(value) ||
    value.forecast_hours !== 48 ||
    !isFiniteNumber(value.load_lb) ||
    !Array.isArray(value.hours) ||
    value.hours.length !== 49 ||
    !Array.isArray(value.points)
  ) {
    throw new Error('The heatmap service returned an incomplete 48-hour forecast.');
  }

  const hours = value.hours.map((item: unknown, index: number) => {
    if (!isRecord(item) || item.hour !== index || typeof item.timestamp_utc !== 'string') {
      throw new Error('The heatmap service returned invalid forecast hours.');
    }
    return { hour: item.hour, timestamp_utc: item.timestamp_utc };
  });
  const points = value.points.map((point: unknown) => {
    if (
      !isRecord(point) ||
      !isFiniteNumber(point.latitude) ||
      !isFiniteNumber(point.longitude) ||
      !Array.isArray(point.route_ids) ||
      !point.route_ids.every((routeId: unknown) => typeof routeId === 'string') ||
      !Array.isArray(point.hourly) ||
      point.hourly.length !== 49
    ) {
      throw new Error('The heatmap service returned an invalid corridor sample.');
    }
    const hourly = point.hourly.map((sample: unknown) => {
      if (
        !isRecord(sample) ||
        !isFiniteNumber(sample.risk_level) ||
        !Number.isInteger(sample.risk_level) ||
        sample.risk_level < 0 ||
        sample.risk_level > 4
      ) {
        throw new Error('The heatmap service returned an invalid hourly risk value.');
      }
      return { risk_level: sample.risk_level };
    });
    return {
      latitude: point.latitude,
      longitude: point.longitude,
      route_ids: point.route_ids,
      hourly,
    };
  });

  return {
    hours,
    points,
    forecast_hours: value.forecast_hours,
    load_lb: value.load_lb,
  };
}

export async function loadHeatmap(payload: HeatmapPayload): Promise<HeatmapResponse> {
  const response = await fetch(`${API_BASE_URL}/api/heatmap/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await readApiError(response, 'Heatmap forecast failed');
  }

  return parseHeatmapResponse(await response.json());
}
