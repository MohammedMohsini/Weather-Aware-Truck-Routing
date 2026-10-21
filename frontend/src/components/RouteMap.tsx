import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import type { LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import type { Checkpoint, RouteSummary, RiskLevel } from '../types/route';

const routeColors = ['#3b82f6', '#22c55e', '#f97316'];
const riskColors: Record<RiskLevel, string> = {
  Low: '#22c55e',
  Moderate: '#facc15',
  High: '#f97316',
  Severe: '#ef4444',
  'No Travel': '#4c1d95',
};

const getRisk = (checkpoint: Checkpoint): RiskLevel => checkpoint.risk ?? 'Low';

const getMapBounds = (routes: RouteSummary[]): LatLngBoundsExpression => {
  const points = routes.flatMap((route) => route.geometry);
  if (!points.length) {
    return [[40.7128, -74.006], [41.8781, -87.6298]];
  }
  return points;
};

function FitMapBounds({ routes }: { routes: RouteSummary[] }) {
  const map = useMap();

  if (routes.length === 0) {
    return null;
  }

  const bounds = getMapBounds(routes);
  map.fitBounds(bounds, { padding: [24, 24] });
  return null;
}

type RouteMapProps = {
  routes: RouteSummary[];
  selectedRouteId: string;
  onRouteSelect: (routeId: string) => void;
  onCheckpointSelect: (checkpoint: Checkpoint) => void;
};

export function RouteMap({ routes, selectedRouteId, onRouteSelect, onCheckpointSelect }: RouteMapProps) {
  return (
    <div className="map-shell">
      <MapContainer center={[39.5, -96.3]} zoom={4} scrollWheelZoom className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitMapBounds routes={routes} />

        {routes.map((route, index) => {
          const isSelected = selectedRouteId === route.route_id;
          return (
            <Polyline
              key={route.route_id}
              positions={route.geometry}
              pathOptions={{
                color: isSelected ? '#fbbf24' : routeColors[index % routeColors.length],
                weight: isSelected ? 7 : 5,
                opacity: isSelected ? 1 : 0.9,
              }}
              eventHandlers={{ click: () => onRouteSelect(route.route_id) }}
            />
          );
        })}

        {routes.flatMap((route) =>
          route.checkpoints.map((checkpoint) => {
            const risk = getRisk(checkpoint);
            const isSelectedRoute = selectedRouteId === route.route_id;
            return (
              <CircleMarker
                key={`${route.route_id}-${checkpoint.index}`}
                center={[checkpoint.latitude, checkpoint.longitude]}
                radius={isSelectedRoute ? 6 : 5}
                pathOptions={{
                  color: riskColors[risk],
                  fillColor: riskColors[risk],
                  fillOpacity: 0.95,
                  weight: 1,
                }}
                eventHandlers={{ click: () => onCheckpointSelect(checkpoint) }}
              >
                <Popup>
                  <strong>{risk}</strong>
                  <br />
                  ETA: {new Date(checkpoint.eta_utc).toLocaleString()}
                  <br />
                  Wind: {checkpoint.wind_mph ?? 'n/a'} mph
                  <br />
                  Rain: {checkpoint.rain_in_hr ?? 'n/a'} in/hr
                  <br />
                  Snow: {checkpoint.snow_in_hr ?? 'n/a'} in/hr
                  <br />
                  {checkpoint.reason ?? 'Weather risk checkpoint'}
                </Popup>
              </CircleMarker>
            );
          }),
        )}
      </MapContainer>
    </div>
  );
}
