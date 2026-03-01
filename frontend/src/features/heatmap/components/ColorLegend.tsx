"use client";

import { useEffect, useRef } from "react";

import { TEMP_MAX, TEMP_MIN, tempToColor } from "../lib/color-scale";

const LEGEND_HEIGHT = 16;

export function ColorLegend() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const container = canvas.parentElement;
    if (!container) return;

    const draw = () => {
      const width = container.clientWidth;
      if (width === 0) return;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = LEGEND_HEIGHT * dpr;
      canvas.style.height = `${LEGEND_HEIGHT}px`;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.scale(dpr, dpr);

      for (let x = 0; x < width; x++) {
        const temp = TEMP_MIN + (x / width) * (TEMP_MAX - TEMP_MIN);
        ctx.fillStyle = tempToColor(temp);
        ctx.fillRect(x, 0, 1, LEGEND_HEIGHT);
      }
    };

    draw();

    const observer = new ResizeObserver(() => draw());
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  const labels = Array.from({ length: 6 }, (_, i) => TEMP_MIN + i * 10);

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
              left: `${((temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)) * 100}%`,
              transform: "translateX(-50%)",
            }}
          >
            {temp}℃
          </span>
        ))}
      </div>
    </div>
  );
}
