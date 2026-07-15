'use client';

import { useEffect, useRef } from 'react';

import { MAX_TEMPERATURE, MIN_TEMPERATURE, tempToColor } from '../libs/color-scale';

const LEGEND_HEIGHT = 16;

export function ColorLegend(): React.JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const container = canvas.parentElement;
    if (!container) return;

    const draw = (): void => {
      const width = container.clientWidth;
      if (width === 0) return;

      const devicePixelRatio = window.devicePixelRatio || 1;
      canvas.width = width * devicePixelRatio;
      canvas.height = LEGEND_HEIGHT * devicePixelRatio;
      canvas.style.height = `${LEGEND_HEIGHT}px`;

      const context = canvas.getContext('2d');
      if (!context) return;

      context.scale(devicePixelRatio, devicePixelRatio);

      for (let horizontalPosition = 0; horizontalPosition < width; horizontalPosition++) {
        const temperature = MIN_TEMPERATURE + (horizontalPosition / width) * (MAX_TEMPERATURE - MIN_TEMPERATURE);
        context.fillStyle = tempToColor(temperature);
        context.fillRect(horizontalPosition, 0, 1, LEGEND_HEIGHT);
      }
    };

    draw();

    const observer = new ResizeObserver(draw);
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  const labels = Array.from({ length: 6 }, (_, index) => MIN_TEMPERATURE + index * 10);

  return (
    <div className="flex flex-col items-start gap-1 w-full max-w-[300px]">
      <canvas ref={canvasRef} className="w-full" />
      <div className="relative text-xs text-muted-foreground w-full h-4">
        {labels.map((temp) => (
          <span
            key={temp}
            className="absolute text-center"
            style={{
              /* 動的な left 値は Tailwind では表現できないためインラインスタイルを使用 */
              left: `${((temp - MIN_TEMPERATURE) / (MAX_TEMPERATURE - MIN_TEMPERATURE)) * 100}%`,
              transform: 'translateX(-50%)',
            }}
          >
            {temp}℃
          </span>
        ))}
      </div>
    </div>
  );
}
