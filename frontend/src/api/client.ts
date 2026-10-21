import type { RouteSummary } from '../types/route';

export type AnalyzePayload = {
  origin: string;
  destination: string;
  departure_time: string;
  load_lb: number;
  interval_miles: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const parseRoutes = (payload: any): RouteSummary[] => {
  if (!payload?.routes || !Array.isArray(payload.routes)) {
    return [];
  }

  return payload.routes.map((route: any, index: number) => ({
    route_id: route.route_id ?? `route-${index + 1}`,
    geometry: Array.isArray(route.geometry) ? route.geometry : [],
    total_distance_miles: Number(route.total_distance_miles ?? 0),
    total_duration_seconds: Number(route.total_duration_seconds ?? 0),
    summary: route.summary ?? `Route ${index + 1}`,
    recommended: Boolean(route.recommended ?? index === 0),
    checkpoints: Array.isArray(route.checkpoints) ? route.checkpoints : [],
    metrics: route.metrics ?? {
      no_travel_miles: 0,
      severe_miles: 0,
      high_miles: 0,
      average_risk: 0,
      miles_by_level: { Low: 0, Moderate: 0, High: 0, Severe: 0, 'No Travel': 0 },
    },
  }));
};

export async function analyzeRoutes(payload: AnalyzePayload): Promise<RouteSummary[]> {
  const response = await fetch(`${API_BASE_URL}/api/analyze/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Routing analysis failed.');
  }

  const data = await response.json();
  return parseRoutes(data);
}
