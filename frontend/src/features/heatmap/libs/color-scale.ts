export const MIN_TEMPERATURE = -10;
export const MAX_TEMPERATURE = 40;
export const TEMPERATURE_RANGE = MAX_TEMPERATURE - MIN_TEMPERATURE;

// Color stops: temp -> [r, g, b]
type RgbColor = [red: number, green: number, blue: number];
type ColorStop = [temperature: number, color: RgbColor];

const COLOR_STOPS: ColorStop[] = [
  [-10, [0, 0, 180]], // dark blue
  [0, [100, 150, 255]], // light blue
  [15, [255, 255, 150]], // light yellow
  [30, [255, 165, 0]], // orange
  [40, [180, 0, 0]], // dark red
];

function interpolate(start: number, end: number, ratio: number): number {
  return start + (end - start) * ratio;
}

export function tempToColor(temp: number | null): string {
  if (temp === null || temp === undefined) {
    return 'rgba(200, 200, 200, 0.3)';
  }

  // Clamp to range
  if (temp <= COLOR_STOPS[0][0]) {
    const [red, green, blue] = COLOR_STOPS[0][1];
    return `rgb(${red},${green},${blue})`;
  }
  if (temp >= COLOR_STOPS[COLOR_STOPS.length - 1][0]) {
    const [red, green, blue] = COLOR_STOPS[COLOR_STOPS.length - 1][1];
    return `rgb(${red},${green},${blue})`;
  }

  // Find the two stops to interpolate between
  for (let stopIndex = 0; stopIndex < COLOR_STOPS.length - 1; stopIndex++) {
    const [lowerTemperature, lowerColor] = COLOR_STOPS[stopIndex];
    const [upperTemperature, upperColor] = COLOR_STOPS[stopIndex + 1];
    if (temp >= lowerTemperature && temp <= upperTemperature) {
      const ratio = (temp - lowerTemperature) / (upperTemperature - lowerTemperature);
      const red = Math.round(interpolate(lowerColor[0], upperColor[0], ratio));
      const green = Math.round(interpolate(lowerColor[1], upperColor[1], ratio));
      const blue = Math.round(interpolate(lowerColor[2], upperColor[2], ratio));
      return `rgb(${red},${green},${blue})`;
    }
  }

  return 'rgba(200, 200, 200, 0.3)';
}

// Pre-compute gradient for legend rendering
export function getGradientStops(): { offset: string; color: string }[] {
  return COLOR_STOPS.map(([temperature, [red, green, blue]]) => ({
    offset: `${((temperature - MIN_TEMPERATURE) / TEMPERATURE_RANGE) * 100}%`,
    color: `rgb(${red},${green},${blue})`,
  }));
}
