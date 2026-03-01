export const TEMP_MIN = -10;
export const TEMP_MAX = 40;
export const TEMP_RANGE = TEMP_MAX - TEMP_MIN;

// Color stops: temp -> [r, g, b]
const COLOR_STOPS: [number, [number, number, number]][] = [
  [-10, [0, 0, 180]], // dark blue
  [0, [100, 150, 255]], // light blue
  [15, [255, 255, 150]], // light yellow
  [30, [255, 165, 0]], // orange
  [40, [180, 0, 0]], // dark red
];

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function tempToColor(temp: number | null): string {
  if (temp === null || temp === undefined) {
    return "rgba(200, 200, 200, 0.3)";
  }

  // Clamp to range
  if (temp <= COLOR_STOPS[0][0]) {
    const [r, g, b] = COLOR_STOPS[0][1];
    return `rgb(${r},${g},${b})`;
  }
  if (temp >= COLOR_STOPS[COLOR_STOPS.length - 1][0]) {
    const [r, g, b] = COLOR_STOPS[COLOR_STOPS.length - 1][1];
    return `rgb(${r},${g},${b})`;
  }

  // Find the two stops to interpolate between
  for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
    const [t0, c0] = COLOR_STOPS[i];
    const [t1, c1] = COLOR_STOPS[i + 1];
    if (temp >= t0 && temp <= t1) {
      const t = (temp - t0) / (t1 - t0);
      const r = Math.round(lerp(c0[0], c1[0], t));
      const g = Math.round(lerp(c0[1], c1[1], t));
      const b = Math.round(lerp(c0[2], c1[2], t));
      return `rgb(${r},${g},${b})`;
    }
  }

  return "rgba(200, 200, 200, 0.3)";
}

// Pre-compute gradient for legend rendering
export function getGradientStops(): { offset: string; color: string }[] {
  return COLOR_STOPS.map(([temp, [r, g, b]]) => ({
    offset: `${((temp - TEMP_MIN) / TEMP_RANGE) * 100}%`,
    color: `rgb(${r},${g},${b})`,
  }));
}
