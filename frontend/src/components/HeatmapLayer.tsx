import { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';

export type HeatmapPoint = {
  lat: number;
  lng: number;
  risk: number;
};

const riskColors = ['#22c55e', '#facc15', '#f97316', '#ef4444', '#4c1d95'];

export function HeatmapLayer({ points, hour }: { points: HeatmapPoint[]; hour: number }) {
  const map = useMap();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const render = () => {
      const size = map.getSize();
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return;
      }

      canvas.width = size.x;
      canvas.height = size.y;
      ctx.clearRect(0, 0, size.x, size.y);

      for (const point of points) {
        const pixel = map.latLngToContainerPoint([point.lat, point.lng]);
        const levelIndex = Math.min(riskColors.length - 1, Math.max(0, Math.round(point.risk)));
        const riskColor = riskColors[levelIndex];
        const adjustedHour = hour + ((point.lat + point.lng) % 2) * 0.35;
        const normalizedRisk = Math.max(0, Math.min(1, (point.risk + adjustedHour * 0.02) / 5));
        const radius = 18 + normalizedRisk * 32;

        const gradient = ctx.createRadialGradient(pixel.x, pixel.y, 2, pixel.x, pixel.y, radius);
        const alpha = 0.18 + normalizedRisk * 0.52;
        gradient.addColorStop(0, `${riskColor}cc`);
        gradient.addColorStop(0.4, `${riskColor}99`);
        gradient.addColorStop(1, `${riskColor}00`);

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pixel.x, pixel.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = alpha;
        ctx.fillStyle = riskColor;
        ctx.beginPath();
        ctx.arc(pixel.x, pixel.y, 4 + normalizedRisk * 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }
    };

    render();
    map.on('move zoom resize', render);
    return () => {
      map.off('move zoom resize', render);
    };
  }, [hour, map, points]);

  return <canvas ref={canvasRef} className="heatmap-canvas" aria-hidden="true" />;
}
