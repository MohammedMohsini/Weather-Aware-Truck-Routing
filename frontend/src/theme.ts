import type { RiskLevel } from './types/route';

export const riskLevels: RiskLevel[] = ['Low', 'Moderate', 'High', 'Severe', 'No Travel'];

const riskVariable: Record<RiskLevel, string> = {
  Low: '--risk-low',
  Moderate: '--risk-moderate',
  High: '--risk-high',
  Severe: '--risk-severe',
  'No Travel': '--risk-no-travel',
};

export function getRiskColor(level: RiskLevel): string {
  return getComputedStyle(document.documentElement).getPropertyValue(riskVariable[level]).trim();
}

export function getRiskColorByLevel(level: number): string {
  const risk = riskLevels[Math.max(0, Math.min(riskLevels.length - 1, Math.round(level)))];
  return getRiskColor(risk);
}

export function getRouteColor(index: number): string {
  const variable = ['--route-one', '--route-two', '--route-three'][index % 3];
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}
