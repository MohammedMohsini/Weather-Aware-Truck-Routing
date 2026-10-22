import { useEffect, useMemo, useState } from 'react';

import { analyzeRoutes } from './api/client';
import type { HeatmapPoint } from './components/HeatmapLayer';
import { HeatmapSlider } from './components/HeatmapSlider';
import { RouteForm } from './components/RouteForm';
import { RouteMap } from './components/RouteMap';
import { RouteSummaryCard } from './components/RouteSummaryCard';
import type { Checkpoint, RouteSummary } from './types/route';
import './App.css';

const now = new Date(Date.now() + 60 * 60 * 1000);
const defaultForm = {
  origin: 'New York, NY',
  destination: 'Chicago, IL',
  departure_time: now.toISOString().slice(0, 16),
  load_lb: 28000,
  interval_miles: 25,
};

const routeOneGeometry = [
  [40.7128, -74.006],
  [40.92, -75.75],
  [41.14, -77.37],
  [41.6, -80.4],
  [41.88, -87.63],
] as [number, number][];

const routeTwoGeometry = [
  [40.7128, -74.006],
  [40.5, -76.2],
  [40.68, -79.8],
  [41.1, -82.8],
  [41.34, -85.6],
  [41.88, -87.63],
] as [number, number][];

const routeThreeGeometry = [
  [40.7128, -74.006],
  [39.95, -77.4],
  [40.05, -81.2],
  [41.15, -84.8],
  [41.88, -87.63],
] as [number, number][];

const makeCheckpoints = (geometry: [number, number][]): Checkpoint[] => {
  const values = [
    { index: 0, distance: 0, eta: '2026-10-21T14:00:00Z', risk: 'Low', wind_mph: 18, rain_in_hr: 0.03, snow_in_hr: 0.0, reason: 'Minimal weather exposure.' },
    { index: 1, distance: 180, eta: '2026-10-21T16:40:00Z', risk: 'Moderate', wind_mph: 29, rain_in_hr: 0.18, snow_in_hr: 0.0, reason: 'Wind and light rain are within moderate thresholds.' },
    { index: 2, distance: 380, eta: '2026-10-21T19:10:00Z', risk: 'High', wind_mph: 39, rain_in_hr: 0.32, snow_in_hr: 0.0, reason: 'Crosswinds and rain raise the risk to High.' },
    { index: 3, distance: 560, eta: '2026-10-21T21:20:00Z', risk: 'Severe', wind_mph: 47, rain_in_hr: 0.42, snow_in_hr: 0.0, reason: 'Wind meets the severe threshold for this load.' },
    { index: 4, distance: 680, eta: '2026-10-21T23:50:00Z', risk: 'Low', wind_mph: 20, rain_in_hr: 0.05, snow_in_hr: 0.0, reason: 'Conditions stabilize on the final segment.' },
  ];

  return values.map((value, idx) => {
    const point = geometry[Math.min(idx, geometry.length - 1)];
    return {
      index: value.index,
      latitude: point[0],
      longitude: point[1],
      distance_from_start_miles: value.distance,
      segment_length_miles: idx === 0 ? 0 : 180,
      eta_utc: value.eta,
      risk: value.risk as Checkpoint['risk'],
      reason: value.reason,
      wind_mph: value.wind_mph,
      rain_in_hr: value.rain_in_hr,
      snow_in_hr: value.snow_in_hr,
    };
  });
};

const buildDemoRoutes = (): RouteSummary[] => [
  {
    route_id: 'route-1',
    geometry: routeOneGeometry,
    total_distance_miles: 730,
    total_duration_seconds: 17520,
    summary: 'I-80 corridor with higher wind exposure near the Great Lakes.',
    recommended: true,
    checkpoints: makeCheckpoints(routeOneGeometry),
    metrics: {
      no_travel_miles: 0,
      severe_miles: 20,
      high_miles: 80,
      average_risk: 2.3,
      miles_by_level: { Low: 400, Moderate: 180, High: 80, Severe: 20, 'No Travel': 0 },
    },
  },
  {
    route_id: 'route-2',
    geometry: routeTwoGeometry,
    total_distance_miles: 760,
    total_duration_seconds: 18180,
    summary: 'Midwest route with slightly longer travel time but milder weather.',
    recommended: false,
    checkpoints: makeCheckpoints(routeTwoGeometry),
    metrics: {
      no_travel_miles: 0,
      severe_miles: 40,
      high_miles: 120,
      average_risk: 2.5,
      miles_by_level: { Low: 430, Moderate: 180, High: 100, Severe: 40, 'No Travel': 0 },
    },
  },
  {
    route_id: 'route-3',
    geometry: routeThreeGeometry,
    total_distance_miles: 790,
    total_duration_seconds: 18720,
    summary: 'Southern detour with the lowest average risk but longer duration.',
    recommended: false,
    checkpoints: makeCheckpoints(routeThreeGeometry),
    metrics: {
      no_travel_miles: 0,
      severe_miles: 10,
      high_miles: 60,
      average_risk: 2.2,
      miles_by_level: { Low: 470, Moderate: 180, High: 80, Severe: 10, 'No Travel': 0 },
    },
  },
];

const buildHeatmapPoints = (routes: RouteSummary[]): HeatmapPoint[] => {
  const points: HeatmapPoint[] = [];

  routes.forEach((route) => {
    const geometry = route.geometry;
    for (let index = 0; index < geometry.length - 1; index += 1) {
      const [lat1, lng1] = geometry[index];
      const [lat2, lng2] = geometry[index + 1];
      const segments = 6;

      for (let segmentIndex = 0; segmentIndex <= segments; segmentIndex += 1) {
        const t = segmentIndex / segments;
        const lat = lat1 + (lat2 - lat1) * t;
        const lng = lng1 + (lng2 - lng1) * t;
        const risk = ((Math.sin((lat + lng) * 14 + index) + Math.cos((lat - lng) * 17 + route.total_distance_miles / 200)) + 2) / 4;

        points.push({
          lat,
          lng,
          risk: Math.max(0, Math.min(4, risk * 4 + (route.recommended ? 0.5 : 0.25))),
        });
      }
    }
  });

  return points;
};

function App() {
  const [form, setForm] = useState(defaultForm);
  const [routes, setRoutes] = useState<RouteSummary[]>(() => buildDemoRoutes());
  const [selectedRouteId, setSelectedRouteId] = useState('route-1');
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatmapHour, setHeatmapHour] = useState(12);
  const [playing, setPlaying] = useState(false);

  const heatmapPoints = useMemo(() => buildHeatmapPoints(routes), [routes]);
  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? routes[0];

  useEffect(() => {
    if (!playing) {
      return;
    }

    const timer = window.setInterval(() => {
      setHeatmapHour((currentHour) => (currentHour >= 48 ? 0 : currentHour + 1));
    }, 600);

    return () => window.clearInterval(timer);
  }, [playing]);

  const updateField = (field: keyof typeof defaultForm, value: string | number) => {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);

    try {
      const nextRoutes = await analyzeRoutes({
        origin: form.origin,
        destination: form.destination,
        departure_time: `${form.departure_time}:00Z`,
        load_lb: Number(form.load_lb),
        interval_miles: Number(form.interval_miles),
      });

      if (nextRoutes.length > 0) {
        setRoutes(nextRoutes);
        const activeRouteId = nextRoutes.find((route) => route.recommended)?.route_id ?? nextRoutes[0].route_id;
        setSelectedRouteId(activeRouteId);
        return;
      }

      throw new Error('No routes were returned by the analysis service.');
    } catch (analysisError) {
      console.error(analysisError);
      const fallbackRoutes = buildDemoRoutes();
      setRoutes(fallbackRoutes);
      setSelectedRouteId('route-1');
      setError('Routing service unavailable — showing demo route analysis.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Route intelligence</p>
          <h1>Weather-Aware Truck Routing</h1>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="left-panel">
          <RouteForm values={form} onChange={updateField} onSubmit={handleAnalyze} loading={loading} />
        </aside>

        <main className="map-panel">
          <RouteMap
            routes={routes}
            selectedRouteId={selectedRouteId}
            heatmapPoints={heatmapPoints}
            heatmapHour={heatmapHour}
            onRouteSelect={setSelectedRouteId}
            onCheckpointSelect={setSelectedCheckpoint}
          />
          <div className="heatmap-wrapper">
            <HeatmapSlider
              hour={heatmapHour}
              onHourChange={setHeatmapHour}
              playing={playing}
              onTogglePlay={() => setPlaying((current) => !current)}
            />
          </div>
        </main>
      </div>

      {error ? <div className="status-banner">{error}</div> : null}

      <div className="sidebar-grid">
        <section className="summary-list">
          {routes.map((route) => (
            <RouteSummaryCard
              key={route.route_id}
              route={route}
              isSelected={route.route_id === selectedRouteId}
              onSelect={() => setSelectedRouteId(route.route_id)}
            />
          ))}
        </section>

        <section className="detail-panel">
          <h2>{selectedRoute?.summary}</h2>
          <div className="detail-metrics">
            <div>
              <span>Distance</span>
              <strong>{selectedRoute?.total_distance_miles.toFixed(0)} mi</strong>
            </div>
            <div>
              <span>Duration</span>
              <strong>{((selectedRoute?.total_duration_seconds ?? 0) / 3600).toFixed(1)} hrs</strong>
            </div>
            <div>
              <span>Avg risk</span>
              <strong>{selectedRoute?.metrics?.average_risk.toFixed(1) ?? '0.0'}</strong>
            </div>
          </div>

          {selectedCheckpoint ? (
            <div className="checkpoint-card">
              <h3>Selected checkpoint</h3>
              <ul>
                <li>ETA: {new Date(selectedCheckpoint.eta_utc).toLocaleString()}</li>
                <li>Wind: {selectedCheckpoint.wind_mph ?? 'n/a'} mph</li>
                <li>Rain: {selectedCheckpoint.rain_in_hr ?? 'n/a'} in/hr</li>
                <li>Snow: {selectedCheckpoint.snow_in_hr ?? 'n/a'} in/hr</li>
                <li>Risk: {selectedCheckpoint.risk ?? 'Low'}</li>
              </ul>
              <p>{selectedCheckpoint.reason ?? 'Weather condition tracked at this checkpoint.'}</p>
            </div>
          ) : (
            <div className="checkpoint-card muted">
              Click a checkpoint on the map to inspect the ETA, weather conditions, and risk explanation.
            </div>
          )}

          <div className="heatmap-panel">
            <h3>Forecast heatmap</h3>
            <div className="heatmap-legend">
              <span>Low</span>
              <span>Moderate</span>
              <span>High</span>
              <span>Severe</span>
              <span>No Travel</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default App;
