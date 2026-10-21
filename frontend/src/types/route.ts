export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel';

export type RoutePoint = [number, number];

export type Checkpoint = {
  index: number;
  latitude: number;
  longitude: number;
  distance_from_start_miles: number;
  segment_length_miles: number;
  eta_utc: string;
  risk?: RiskLevel;
  reason?: string;
  wind_mph?: number;
  rain_in_hr?: number;
  snow_in_hr?: number;
};

export type RouteMetrics = {
  no_travel_miles: number;
  severe_miles: number;
  high_miles: number;
  average_risk: number;
  miles_by_level: Record<string, number>;
};

export type RouteSummary = {
  route_id: string;
  geometry: RoutePoint[];
  total_distance_miles: number;
  total_duration_seconds: number;
  summary: string;
  recommended: boolean;
  checkpoints: Checkpoint[];
  metrics?: RouteMetrics;
};
