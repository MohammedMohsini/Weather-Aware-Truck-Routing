import type { CSSProperties } from 'react';
import type { RouteSummary } from '../types/route';
import { riskLevels } from '../theme';

export function RouteSummaryCard({
  route,
  isSelected,
  onSelect,
  explanation,
}: {
  route: RouteSummary;
  isSelected: boolean;
  onSelect: () => void;
  explanation: string;
}) {
  const metrics = route.metrics ?? {
    no_travel_miles: 0,
    severe_miles: 0,
    high_miles: 0,
    average_risk: 0,
    miles_by_level: { Low: 0, Moderate: 0, High: 0, Severe: 0, 'No Travel': 0 },
  };
  const routeMiles = riskLevels.reduce((sum, level) => sum + (metrics.miles_by_level[level] ?? 0), 0);

  return (
    <article className={`summary-card ${isSelected ? 'selected' : ''}`}>
      <button type="button" className="route-card-select" aria-pressed={isSelected} onClick={onSelect}>
        <span className="route-card-title">
          <span>
            <span className="summary-label">{route.route_id}</span>
            {route.recommended ? <span className="recommendation-badge">Recommended</span> : null}
          </span>
          <strong>{route.total_distance_miles.toFixed(0)} mi</strong>
        </span>
        <span className="summary-meta">
          <span>{(route.total_duration_seconds / 3600).toFixed(1)} hrs</span>
          <span>Distance-weighted risk {metrics.average_risk.toFixed(2)}</span>
        </span>
        <span className="risk-stacked-bar" role="img" aria-label={`${route.route_id} miles by risk level`}>
          {riskLevels.map((level) => {
            const miles = metrics.miles_by_level[level] ?? 0;
            return (
              <span
                key={level}
                style={
                  {
                    '--risk-color': `var(--risk-${level.toLowerCase().replace(' ', '-')})`,
                    width: `${routeMiles > 0 ? (miles / routeMiles) * 100 : 0}%`,
                  } as CSSProperties
                }
                title={`${level}: ${miles.toFixed(1)} miles`}
              />
            );
          })}
        </span>
        <span className="risk-legend" role="list" aria-label="Miles by risk level">
          {riskLevels.map((level) => (
            <span className="risk-legend-item" role="listitem" key={level}>
              <span
                className="risk-swatch"
                style={
                  { '--risk-color': `var(--risk-${level.toLowerCase().replace(' ', '-')})` } as CSSProperties
                }
                aria-hidden="true"
              />
              <span>{level}</span>
              <strong>{(metrics.miles_by_level[level] ?? 0).toFixed(0)}</strong>
            </span>
          ))}
        </span>
        <span className="summary-note">{route.summary}</span>
      </button>
      <details className="why-panel">
        <summary>Why this route</summary>
        <p>{explanation}</p>
      </details>
    </article>
  );
}
