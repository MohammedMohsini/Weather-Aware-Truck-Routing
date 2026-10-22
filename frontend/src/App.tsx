import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { analyzeRoutes, loadHeatmap, pingApi, type HeatmapPayload, type HeatmapResponse } from './api/client';
import type { HeatmapPoint } from './components/HeatmapLayer';
import { CheckpointList } from './components/CheckpointList';
import { HeatmapSlider } from './components/HeatmapSlider';
import { RouteForm } from './components/RouteForm';
import { RouteSummaryCard } from './components/RouteSummaryCard';
import type { HoveredCheckpoint } from './components/RouteMap';
import { setSelectedHeatmapHour } from './stores/heatmapHour';
import type { Checkpoint, RouteSummary } from './types/route';
import './App.css';

const RouteMap = lazy(() => import('./components/RouteMap').then((module) => ({ default: module.RouteMap })));

const toLocalDateTimeInput = (date: Date): string => {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 16);
};

const initialForm = {
  origin: '',
  destination: '',
  departure_time: toLocalDateTimeInput(new Date(Date.now() + 60 * 60 * 1000)),
  load_lb: 28000,
  interval_miles: 25,
};

type ServerState = 'checking' | 'ready' | 'waking';

function userFacingError(error: unknown): string {
  const message = error instanceof Error ? error.message : 'Route analysis failed. Please try again.';
  const normalized = message.toLowerCase();
  if (normalized.includes('geocod')) {
    return `Location lookup failed. Check the origin and destination, then try again. ${message}`;
  }
  if (normalized.includes('forecast') || normalized.includes('weather data')) {
    return `Departure time is outside the available forecast window, or forecast coverage is incomplete. Choose a departure time within the forecast range. ${message}`;
  }
  if (
    normalized.includes('provider') ||
    normalized.includes('routing is unavailable') ||
    normalized.includes('openrouteservice')
  ) {
    return `A routing or weather provider is unavailable. Please try again later. ${message}`;
  }
  if (normalized.includes('failed to fetch') || normalized.includes('networkerror')) {
    return 'The server may be waking up or temporarily unavailable. Wait a moment and retry.';
  }
  return message;
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [routes, setRoutes] = useState<RouteSummary[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState('');
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(null);
  const [hoveredCheckpoint, setHoveredCheckpoint] = useState<HoveredCheckpoint>(null);
  const [loading, setLoading] = useState(false);
  const [progressMessage, setProgressMessage] = useState('');
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [heatmapError, setHeatmapError] = useState<string | null>(null);
  const [heatmapPayload, setHeatmapPayload] = useState<HeatmapPayload | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const [serverState, setServerState] = useState<ServerState>('checking');
  const heatmapRequestId = useRef(0);

  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? routes[0];
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const heatmapPoints = useMemo<HeatmapPoint[]>(
    () =>
      heatmapData?.points.map((point) => ({
        lat: point.latitude,
        lng: point.longitude,
        hourlyRiskLevels: point.hourly.map((sample) => sample.risk_level),
      })) ?? [],
    [heatmapData],
  );
  useEffect(() => {
    const wakeTimer = window.setTimeout(() => {
      setServerState((current) => (current === 'ready' ? current : 'waking'));
    }, 1800);
    void pingApi()
      .then(() => setServerState('ready'))
      .catch(() => setServerState('waking'))
      .finally(() => window.clearTimeout(wakeTimer));
    return () => window.clearTimeout(wakeTimer);
  }, []);

  const updateField = useCallback((field: keyof typeof initialForm, value: string | number) => {
    setForm((current) => ({ ...current, [field]: value }));
  }, []);

  const requestHeatmap = useCallback(async (payload: HeatmapPayload) => {
    const requestId = ++heatmapRequestId.current;
    setHeatmapPayload(payload);
    setHeatmapData(null);
    setHeatmapError(null);
    setHeatmapLoading(true);
    try {
      const data = await loadHeatmap(payload);
      if (requestId === heatmapRequestId.current) {
        setHeatmapData(data);
      }
    } catch (heatmapLoadError) {
      if (requestId === heatmapRequestId.current) {
        setHeatmapError(userFacingError(heatmapLoadError));
      }
    } finally {
      if (requestId === heatmapRequestId.current) {
        setHeatmapLoading(false);
      }
    }
  }, []);

  const handleAnalyze = useCallback(async () => {
    heatmapRequestId.current += 1;
    setHeatmapLoading(false);
    setHeatmapData(null);
    setHeatmapPayload(null);
    setLoading(true);
    setProgressMessage('Fetching routes…');
    setError(null);
    setHeatmapError(null);
    setSelectedCheckpoint(null);
    setHoveredCheckpoint(null);
    const stageTimers = [
      window.setTimeout(() => setProgressMessage('Sampling checkpoint weather…'), 2200),
      window.setTimeout(() => setProgressMessage('Scoring route risk…'), 4800),
    ];
    const departureTime = new Date(form.departure_time).toISOString();

    try {
      const nextRoutes = await analyzeRoutes({
        origin: form.origin,
        destination: form.destination,
        departure_time: departureTime,
        load_lb: Number(form.load_lb),
        interval_miles: Number(form.interval_miles),
      });
      if (!nextRoutes.length) {
        throw new Error('The analysis service returned no routes. Please try again.');
      }
      setRoutes(nextRoutes);
      setSelectedRouteId(nextRoutes.find((route) => route.recommended)?.route_id ?? nextRoutes[0].route_id);
      setSelectedHeatmapHour(0);
      setLoading(false);
      setProgressMessage('');
      await requestHeatmap({
        route_geometries: nextRoutes.map((route) => route.geometry),
        start_time: departureTime,
        load_lb: Number(form.load_lb),
      });
    } catch (analysisError) {
      setError(userFacingError(analysisError));
    } finally {
      stageTimers.forEach(window.clearTimeout);
      setLoading(false);
      setProgressMessage('');
    }
  }, [form, requestHeatmap]);

  const retryHeatmap = useCallback(() => {
    if (heatmapPayload) {
      void requestHeatmap(heatmapPayload);
    }
  }, [heatmapPayload, requestHeatmap]);

  const fillExample = useCallback(() => {
    const departure = new Date();
    departure.setDate(departure.getDate() + 1);
    departure.setHours(8, 0, 0, 0);
    setForm({
      origin: 'Chicago, IL',
      destination: 'Denver, CO',
      departure_time: toLocalDateTimeInput(departure),
      load_lb: 45000,
      interval_miles: 25,
    });
    setError(null);
  }, []);

  const selectRoute = useCallback((routeId: string) => {
    setSelectedRouteId(routeId);
    setSelectedCheckpoint(null);
    setHoveredCheckpoint(null);
  }, []);

  const selectCheckpoint = useCallback((checkpoint: Checkpoint) => {
    setSelectedCheckpoint(checkpoint);
  }, []);

  const routeExplanation = (route: RouteSummary): string => {
    const metrics = route.metrics;
    if (!metrics) {
      return route.recommendation_explanation ?? 'Risk details are not available for this route.';
    }
    const recommended = routes.find((item) => item.recommended);
    if (route.recommended) {
      return (
        route.recommendation_explanation ??
        `This route is recommended after comparing No Travel miles, Severe miles, High miles, distance-weighted average risk (${metrics.average_risk.toFixed(2)}), and duration.`
      );
    }
    const comparisons = routes
      .filter((otherRoute) => otherRoute.route_id !== route.route_id)
      .map((otherRoute) => {
        const otherMetrics = otherRoute.metrics;
        if (!otherMetrics) {
          return `${otherRoute.route_id}: metrics unavailable`;
        }
        return `${otherRoute.route_id}: ${otherMetrics.no_travel_miles.toFixed(1)} No Travel mi, ${otherMetrics.severe_miles.toFixed(1)} Severe mi, ${otherMetrics.high_miles.toFixed(1)} High mi, average risk ${otherMetrics.average_risk.toFixed(2)}, ${(otherRoute.total_duration_seconds / 3600).toFixed(1)} hr`;
      })
      .join('; ');
    return `This option has ${metrics.no_travel_miles.toFixed(1)} No Travel mi, ${metrics.severe_miles.toFixed(1)} Severe mi, ${metrics.high_miles.toFixed(1)} High mi, distance-weighted average risk ${metrics.average_risk.toFixed(2)}, and ${(route.total_duration_seconds / 3600).toFixed(1)} hr travel time. Comparison: ${comparisons || recommended?.route_id || 'no alternatives available'}.`;
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">
          W
        </div>
        <div>
          <h1 className="brand-title">Weather-Aware Truck Routing</h1>
          <p className="brand-subtitle">Weather intelligence for safer truck journeys</p>
        </div>
      </header>

      {serverState === 'waking' ? (
        <div className="wake-banner" role="status">
          <span className="spinner" aria-hidden="true" />
          The server may be waking up. Its first response can take a little longer.
        </div>
      ) : null}

      <div className="workspace-grid">
        <aside className="left-panel">
          <details className="mobile-controls" open>
            <summary>Trip controls and results</summary>
            <div className="mobile-controls-content">
              <section className="panel-section">
                <h2 className="panel-heading">Plan your trip</h2>
                <RouteForm
                  values={form}
                  onChange={updateField}
                  onSubmit={handleAnalyze}
                  onExample={fillExample}
                  loading={loading}
                  progressMessage={progressMessage}
                />
                {loading ? (
                  <p className="loading-banner" role="status">
                    {progressMessage || 'Analyzing your trip…'}
                  </p>
                ) : null}
              </section>

              <section className="panel-section">
                <div className="section-title-row">
                  <h2 className="panel-heading">Route comparison</h2>
                  {routes.length ? <span className="muted-copy">{routes.length} options</span> : null}
                </div>
                {loading ? (
                  <div className="summary-list" aria-label="Loading route options">
                    <div className="skeleton-card" />
                    <div className="skeleton-card" />
                    <div className="skeleton-card" />
                  </div>
                ) : routes.length ? (
                  <div className="summary-list">
                    {routes.map((route) => (
                      <RouteSummaryCard
                        key={route.route_id}
                        route={route}
                        isSelected={route.route_id === selectedRouteId}
                        onSelect={() => selectRoute(route.route_id)}
                        explanation={routeExplanation(route)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    Enter your trip details and analyze to compare weather-aware routes.
                  </div>
                )}
              </section>

              <section className="panel-section">
                <div className="section-title-row">
                  <h2 className="panel-heading">Weather checkpoints</h2>
                  {selectedRoute ? <span className="muted-copy">{selectedRoute.route_id}</span> : null}
                </div>
                {loading ? (
                  <div className="checkpoint-list" aria-label="Loading checkpoint forecast">
                    <div className="skeleton-row" />
                    <div className="skeleton-row" />
                    <div className="skeleton-row" />
                  </div>
                ) : (
                  <CheckpointList
                    route={selectedRoute}
                    timezone={timezone}
                    selectedCheckpoint={selectedCheckpoint}
                    hoveredCheckpoint={hoveredCheckpoint}
                    onSelect={selectCheckpoint}
                    onHover={setHoveredCheckpoint}
                  />
                )}
              </section>
            </div>
          </details>
        </aside>

        <main className="map-panel">
          <div className="map-heading">
            <h2>Route map</h2>
            {selectedRoute ? <span className="muted-copy">Showing {selectedRoute.route_id}</span> : null}
          </div>
          <Suspense
            fallback={
              <div className="map-shell empty-state" role="status">
                Loading interactive map…
              </div>
            }
          >
            <RouteMap
              routes={routes}
              selectedRouteId={selectedRouteId}
              heatmapPoints={heatmapPoints}
              hoveredCheckpoint={hoveredCheckpoint}
              onRouteSelect={selectRoute}
              onCheckpointSelect={selectCheckpoint}
              onCheckpointHover={setHoveredCheckpoint}
            />
          </Suspense>
          <div className="heatmap-wrapper">
            <HeatmapSlider
              hours={heatmapData?.hours ?? []}
              loading={heatmapLoading}
              enabled={Boolean(heatmapData)}
            />
            {heatmapError ? (
              <div className="heatmap-error" role="status">
                <p className="field-error">{heatmapError}</p>
                <button
                  type="button"
                  className="retry-button"
                  onClick={retryHeatmap}
                  disabled={heatmapLoading}
                >
                  Retry heatmap
                </button>
              </div>
            ) : null}
          </div>
        </main>
      </div>

      {error ? (
        <div className="status-banner" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="retry-button"
            onClick={() => void handleAnalyze()}
            disabled={loading}
          >
            Retry
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default App;
