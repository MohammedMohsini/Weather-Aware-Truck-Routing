import { memo, useEffect, useRef, useSyncExternalStore } from 'react';
import { useMap } from 'react-leaflet';

import { getRiskColorByLevel, riskLevels } from '../theme';
import { getSelectedHeatmapHour, subscribeToHeatmapHour } from '../stores/heatmapHour';

export type HeatmapPoint = {
  lat: number;
  lng: number;
  hourlyRiskLevels: number[];
};

function HeatmapLayerComponent({ points }: { points: HeatmapPoint[] }) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const hour = useSyncExternalStore(subscribeToHeatmapHour, getSelectedHeatmapHour, getSelectedHeatmapHour);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    let frame = 0;
    const palette = riskLevels.map((_, index) => getRiskColorByLevel(index));

    const render = () => {
      window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(() => {
        const size = map.getSize();
        const pixelRatio = window.devicePixelRatio || 1;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          return;
        }
        canvas.width = Math.round(size.x * pixelRatio);
        canvas.height = Math.round(size.y * pixelRatio);
        ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        ctx.clearRect(0, 0, size.x, size.y);

        for (const point of points) {
          const pixel = map.latLngToContainerPoint([point.lat, point.lng]);
          const risk = point.hourlyRiskLevels[hour] ?? 0;
          const color = palette[Math.max(0, Math.min(palette.length - 1, Math.round(risk)))];
          const normalizedRisk = Math.max(0, Math.min(1, risk / 4));
          const radius = 18 + normalizedRisk * 32;
          const gradient = ctx.createRadialGradient(pixel.x, pixel.y, 2, pixel.x, pixel.y, radius);
          gradient.addColorStop(0, `${color}cc`);
          gradient.addColorStop(0.4, `${color}80`);
          gradient.addColorStop(1, `${color}00`);
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(pixel.x, pixel.y, radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 0.2 + normalizedRisk * 0.55;
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(pixel.x, pixel.y, 4 + normalizedRisk * 6, 0, Math.PI * 2);
          ctx.fill();
          ctx.globalAlpha = 1;
        }
      });
    };

    render();
    map.on('move zoom resize', render);
    return () => {
      window.cancelAnimationFrame(frame);
      map.off('move zoom resize', render);
    };
  }, [hour, map, points]);

  return <canvas ref={canvasRef} className="heatmap-canvas" aria-hidden="true" />;
}

export const HeatmapLayer = memo(HeatmapLayerComponent);
