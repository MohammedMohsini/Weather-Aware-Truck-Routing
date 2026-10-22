type Listener = () => void;

let selectedHour = 0;
const listeners = new Set<Listener>();

export function getSelectedHeatmapHour(): number {
  return selectedHour;
}

export function setSelectedHeatmapHour(hour: number): void {
  const nextHour = Math.max(0, Math.min(48, Math.round(hour)));
  if (nextHour === selectedHour) {
    return;
  }
  selectedHour = nextHour;
  listeners.forEach((listener) => listener());
}

export function subscribeToHeatmapHour(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
