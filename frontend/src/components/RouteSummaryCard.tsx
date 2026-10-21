import type { RouteSummary } from '../types/route';

const riskLevels = ['Low', 'Moderate', 'High', 'Severe', 'No Travel'];

export function RouteSummaryCard({
  route,
  isSelected,
  onSelect,
}: {
  route: RouteSummary;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const metrics = route.metrics ?? {
    no_travel_miles: 0,
    severe_miles: 0,
    high_miles: 0,
    average_risk: 0,
    miles_by_level: { Low: 0, Moderate: 0, High: 0, Severe: 0, 'No Travel': 0 },
  };

  return (
    <button type="button" className={`summary-card ${isSelected ? 'selected' : ''}`} onClick={onSelect}>
      <div className="summary-header">
        <div>
          <span className="summary-label">Route {route.route_id}</span>
          {route.recommended ? <span className="recommendation-badge">Recommended</span> : null}
        </div>
        <strong>{route.total_distance_miles.toFixed(0)} mi</strong>
      </div>

      <div className="summary-meta">
        <span>{(route.total_duration_seconds / 3600).toFixed(1)} hrs</span>
        <span>Avg risk {metrics.average_risk.toFixed(1)}</span>
      </div>

      <ul className="risk-legend">
        {riskLevels.map((level) => (
          <li key={level}>
            <span className={`risk-dot ${level.toLowerCase().replace(/\s+/g, '-')}`} />
            <span>{level}</span>
            <strong>{metrics.miles_by_level[level] ?? 0}</strong>
          </li>
        ))}
      </ul>

      <p className="summary-note">{route.summary}</p>
    </button>
  );
}
