import type { CSSProperties } from 'react';
import type { Checkpoint, RouteSummary } from '../types/route';
import type { HoveredCheckpoint } from './RouteMap';

type CheckpointListProps = {
  route: RouteSummary | undefined;
  timezone: string;
  selectedCheckpoint: Checkpoint | null;
  hoveredCheckpoint: HoveredCheckpoint;
  onSelect: (checkpoint: Checkpoint) => void;
  onHover: (checkpoint: HoveredCheckpoint) => void;
};

export function CheckpointList({
  route,
  timezone,
  selectedCheckpoint,
  hoveredCheckpoint,
  onSelect,
  onHover,
}: CheckpointListProps) {
  if (!route) {
    return <div className="checkpoint-empty">Checkpoint details appear after route analysis.</div>;
  }
  if (!route.checkpoints.length) {
    return <div className="checkpoint-empty">No forecast checkpoints are available for this route.</div>;
  }

  return (
    <div className="checkpoint-list" aria-label={`${route.route_id} weather checkpoints`}>
      {route.checkpoints.map((checkpoint) => {
        const risk = checkpoint.risk ?? 'Low';
        const isSelected = selectedCheckpoint?.index === checkpoint.index;
        const isHovered =
          hoveredCheckpoint?.routeId === route.route_id && hoveredCheckpoint.index === checkpoint.index;
        return (
          <button
            type="button"
            key={`${route.route_id}-${checkpoint.index}`}
            className={`checkpoint-row${isSelected || isHovered ? ' active' : ''}`}
            onClick={() => onSelect(checkpoint)}
            onMouseEnter={() => onHover({ routeId: route.route_id, index: checkpoint.index })}
            onMouseLeave={() => onHover(null)}
            onFocus={() => onHover({ routeId: route.route_id, index: checkpoint.index })}
            onBlur={() => onHover(null)}
            aria-label={`Checkpoint ${checkpoint.index + 1}, ${risk}, ETA ${new Date(checkpoint.eta_utc).toLocaleString()}`}
          >
            <span className="checkpoint-time">
              {new Date(checkpoint.eta_utc).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                timeZone: timezone,
              })}
            </span>
            <span
              className="risk-badge"
              style={
                { '--risk-color': `var(--risk-${risk.toLowerCase().replace(' ', '-')})` } as CSSProperties
              }
            >
              {risk}
            </span>
            <span className="checkpoint-weather">
              Wind {checkpoint.wind_mph?.toFixed(1) ?? '—'} mph · Rain{' '}
              {checkpoint.rain_in_hr?.toFixed(2) ?? '—'} in/hr · Snow{' '}
              {checkpoint.snow_in_hr?.toFixed(2) ?? '—'} in/hr
            </span>
            <p className="checkpoint-reason">
              {checkpoint.reason ?? 'Weather conditions assessed for this segment.'}
            </p>
          </button>
        );
      })}
    </div>
  );
}
