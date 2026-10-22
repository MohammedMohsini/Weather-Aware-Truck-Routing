import { memo, useEffect, useMemo, type CSSProperties } from 'react';
import { CircleMarker, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import { divIcon, type LatLngBoundsExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { HeatmapLayer, type HeatmapPoint } from './HeatmapLayer';
import type { Checkpoint, RiskLevel, RouteSummary } from '../types/route';
import { getRiskColor, getRouteColor, riskLevels } from '../theme';

const getRisk = (checkpoint: Checkpoint): RiskLevel => checkpoint.risk ?? 'Low';

function FitSelectedRoute({ route }: { route: RouteSummary | undefined }) {
  const map = useMap();

  useEffect(() => {
    if (!route?.geometry.length) {
      return;
    }
    const bounds: LatLngBoundsExpression = route.geometry;
    map.fitBounds(bounds, { padding: [36, 36], animate: true, duration: 0.55 });
  }, [map, route]);

  return null;
}

function EndpointPins({ route }: { route: RouteSummary | undefined }) {
  const icons = useMemo(
    () => ({
      origin: divIcon({
        className: '',
        html: '<div class="endpoint-icon"><span>A</span></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 28],
      }),
      destination: divIcon({
        className: '',
        html: '<div class="endpoint-icon destination"><span>B</span></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 28],
      }),
    }),
    [],
  );
  if (!route?.geometry.length) {
    return null;
  }
  return (
    <>
      <Marker position={route.geometry[0]} icon={icons.origin}>
        <Popup>Trip origin</Popup>
      </Marker>
      <Marker position={route.geometry[route.geometry.length - 1]} icon={icons.destination}>
        <Popup>Trip destination</Popup>
      </Marker>
    </>
  );
}

export type HoveredCheckpoint = { routeId: string; index: number } | null;

type RouteMapProps = {
  routes: RouteSummary[];
  selectedRouteId: string;
  heatmapPoints: HeatmapPoint[];
  hoveredCheckpoint: HoveredCheckpoint;
  onRouteSelect: (routeId: string) => void;
  onCheckpointSelect: (checkpoint: Checkpoint) => void;
  onCheckpointHover: (checkpoint: HoveredCheckpoint) => void;
};

function RouteMapComponent({
  routes,
  selectedRouteId,
  heatmapPoints,
  hoveredCheckpoint,
  onRouteSelect,
  onCheckpointSelect,
  onCheckpointHover,
}: RouteMapProps) {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const selectedRoute = routes.find((route) => route.route_id === selectedRouteId) ?? routes[0];
  const orderedRoutes = [
    ...routes.filter((route) => route.route_id !== selectedRoute?.route_id),
    ...(selectedRoute ? [selectedRoute] : []),
  ];

  return (
    <div className="map-shell" aria-label="Map showing routes and weather risk checkpoints">
      <MapContainer center={[39.5, -96.3]} zoom={4} scrollWheelZoom className="map-container">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitSelectedRoute route={selectedRoute} />
        <EndpointPins route={selectedRoute} />
        <HeatmapLayer points={heatmapPoints} />

        {orderedRoutes.map((route) => {
          const routeIndex = routes.findIndex((item) => item.route_id === route.route_id);
          const isSelected = selectedRouteId === route.route_id;
          return (
            <Polyline
              key={route.route_id}
              positions={route.geometry}
              pathOptions={{
                color: getRouteColor(routeIndex),
                weight: isSelected ? 7 : 4,
                opacity: isSelected ? 1 : 0.42,
              }}
              eventHandlers={{ click: () => onRouteSelect(route.route_id) }}
            />
          );
        })}

        {routes.flatMap((route) =>
          route.checkpoints.map((checkpoint) => {
            const risk = getRisk(checkpoint);
            const isSelectedRoute = selectedRouteId === route.route_id;
            const isHovered =
              hoveredCheckpoint?.routeId === route.route_id && hoveredCheckpoint.index === checkpoint.index;
            const color = getRiskColor(risk);
            return (
              <CircleMarker
                key={`${route.route_id}-${checkpoint.index}`}
                center={[checkpoint.latitude, checkpoint.longitude]}
                radius={isHovered ? 9 : isSelectedRoute ? 6 : 4}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: isSelectedRoute ? 0.98 : 0.65,
                  weight: isHovered ? 3 : 1,
                }}
                eventHandlers={{
                  click: () => {
                    onRouteSelect(route.route_id);
                    onCheckpointSelect(checkpoint);
                  },
                  mouseover: () => onCheckpointHover({ routeId: route.route_id, index: checkpoint.index }),
                  mouseout: () => onCheckpointHover(null),
                }}
              >
                <Popup>
                  <strong>{risk}</strong>
                  <br />
                  ETA ({timezone}): {new Date(checkpoint.eta_utc).toLocaleString()}
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
      <div className="map-legend" aria-label="Map legend">
        <strong>Checkpoint risk</strong>
        <div className="legend-items">
          {riskLevels.map((risk) => (
            <span
              className="legend-item"
              key={risk}
              style={{ '--risk-color': getRiskColor(risk) } as CSSProperties}
            >
              <span className="risk-swatch" aria-hidden="true" />
              {risk}
            </span>
          ))}
          <span className="legend-item">
            <span className="endpoint-icon-mini origin" />
            Origin
          </span>
          <span className="legend-item">
            <span className="endpoint-icon-mini destination" />
            Destination
          </span>
        </div>
      </div>
    </div>
  );
}

export const RouteMap = memo(RouteMapComponent);
