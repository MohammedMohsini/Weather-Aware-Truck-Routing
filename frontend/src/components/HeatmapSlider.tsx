type HeatmapSliderProps = {
  hour: number;
  onHourChange: (hour: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
};

export function HeatmapSlider({ hour, onHourChange, playing, onTogglePlay }: HeatmapSliderProps) {
  return (
    <div className="heatmap-slider-card">
      <div className="heatmap-header-row">
        <span>Forecast window</span>
        <button type="button" className="play-toggle" onClick={onTogglePlay}>
          {playing ? 'Pause' : 'Play'}
        </button>
      </div>

      <div className="heatmap-value-row">
        <strong>{hour} hr</strong>
        <span>0–48 hr</span>
      </div>

      <input
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        onChange={(event) => onHourChange(Number(event.target.value))}
        aria-label="Heatmap forecast hour"
      />
    </div>
  );
}
