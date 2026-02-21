"use client";

import { useEffect, useRef } from "react";

import { tempToColor } from "../lib/color-scale";

const LEGEND_WIDTH = 300;
const LEGEND_HEIGHT = 16;
const TEMP_MIN = -10;
const TEMP_MAX = 40;

export function ColorLegend() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = LEGEND_WIDTH * dpr;
    canvas.height = LEGEND_HEIGHT * dpr;
    canvas.style.width = `${LEGEND_WIDTH}px`;
    canvas.style.height = `${LEGEND_HEIGHT}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);

    for (let x = 0; x < LEGEND_WIDTH; x++) {
      const temp = TEMP_MIN + (x / LEGEND_WIDTH) * (TEMP_MAX - TEMP_MIN);
      ctx.fillStyle = tempToColor(temp);
      ctx.fillRect(x, 0, 1, LEGEND_HEIGHT);
    }
  }, []);

  const labels = [-10, 0, 10, 20, 30, 40];

  return (
    <div className="flex flex-col items-start gap-1">
      <canvas ref={canvasRef} />
      <div
        className="relative text-xs text-muted-foreground"
        style={{ width: LEGEND_WIDTH, height: 16 }}
      >
        {labels.map((temp) => (
          <span
            key={temp}
            className="absolute text-center"
            style={{
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
