import { useEffect, useState, useSyncExternalStore } from 'react';
import type { CSSProperties } from 'react';

import { riskLevels } from '../theme';
import {
  getSelectedHeatmapHour,
  setSelectedHeatmapHour,
  subscribeToHeatmapHour,
} from '../stores/heatmapHour';

type HeatmapSliderProps = {
  hours: { hour: number; timestamp_utc: string }[];
  loading: boolean;
  enabled: boolean;
};

export function HeatmapSlider({ hours, loading, enabled }: HeatmapSliderProps) {
  const hour = useSyncExternalStore(subscribeToHeatmapHour, getSelectedHeatmapHour, getSelectedHeatmapHour);
  const [playing, setPlaying] = useState(false);
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const timestamp = hours[hour]?.timestamp_utc ?? null;
  const formattedTime = timestamp
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: timezone,
      }).format(new Date(timestamp))
    : enabled
      ? 'Forecast time unavailable'
      : 'Analyze a route to load the forecast';

  useEffect(() => {
    if (!playing || !enabled) {
      return;
    }
    const timer = window.setInterval(() => {
      setSelectedHeatmapHour((getSelectedHeatmapHour() + 1) % 49);
    }, 600);
    return () => window.clearInterval(timer);
  }, [enabled, playing]);

  return (
    <section className="heatmap-slider-card" aria-label="Weather heatmap forecast controls">
      <div className="heatmap-header-row">
        <strong>Weather risk forecast</strong>
        <button
          type="button"
          className="play-toggle"
          onClick={() => setPlaying((current) => !current)}
          disabled={!enabled}
          aria-pressed={playing}
        >
          {playing ? 'Pause' : 'Play'}
        </button>
      </div>

      <div className="heatmap-value-row">
        <strong>{formattedTime}</strong>
        {loading ? (
          <span className="spinner" role="status" aria-label="Loading heatmap forecast" />
        ) : (
          <span>0–48 hr · {timezone}</span>
        )}
      </div>

      <input
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        disabled={!enabled}
        onChange={(event) => setSelectedHeatmapHour(Number(event.target.value))}
        aria-label="Heatmap forecast hour"
        aria-valuetext={`${hour} hours after departure${timestamp ? `, ${formattedTime} ${timezone}` : ''}`}
      />
      <div className="heatmap-legend" aria-label="Heatmap risk legend">
        {riskLevels.map((risk) => (
          <span
            className="legend-item"
            key={risk}
            style={{ '--risk-color': `var(--risk-${risk.toLowerCase().replace(' ', '-')})` } as CSSProperties}
          >
            <span className="risk-swatch" aria-hidden="true" />
            {risk}
          </span>
        ))}
      </div>
    </section>
  );
}
