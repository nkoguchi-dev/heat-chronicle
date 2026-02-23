"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { tempToColor } from "../lib/color-scale";
import {
  type GridCell,
  type HeatmapGrid,
  buildGrid,
  getMonthStartDays,
} from "../lib/data-grid";
import type { TemperatureRecord, TempType } from "@/types/api";

function getCellTemp(cell: GridCell | undefined, tempType: TempType): number | null {
  if (!cell) return null;
  switch (tempType) {
    case "max": return cell.maxTemp;
    case "min": return cell.minTemp;
    case "avg": return cell.avgTemp;
  }
}

const CELL_WIDTH = 3;
const CELL_HEIGHT = 12;
const LEFT_MARGIN = 50;
const TOP_MARGIN = 30;

interface HeatmapProps {
  records: TemperatureRecord[];
  startYear: number;
  endYear: number;
  tempType: TempType;
}

export function Heatmap({ records, startYear, endYear, tempType }: HeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    text: string;
    alignRight: boolean;
  } | null>(null);

  const grid = useMemo(
    () => buildGrid(records, startYear, endYear),
    [records, startYear, endYear]
  );

  const years = endYear - startYear + 1;
  const canvasWidth = LEFT_MARGIN + 366 * CELL_WIDTH;
  const canvasHeight = TOP_MARGIN + years * CELL_HEIGHT;

  const drawHeatmap = useCallback(
    (grid: HeatmapGrid) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = canvasWidth * dpr;
      canvas.height = canvasHeight * dpr;
      canvas.style.width = `${canvasWidth}px`;
      canvas.style.height = `${canvasHeight}px`;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, canvasWidth, canvasHeight);

      // Draw month labels
      ctx.fillStyle = "#666";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      const months = getMonthStartDays();
      for (const { label, day } of months) {
        ctx.fillText(label, LEFT_MARGIN + day * CELL_WIDTH + 12, TOP_MARGIN - 8);
      }

      // Draw year labels and cells
      for (let yi = 0; yi < years; yi++) {
        const year = endYear - yi;
        const y = TOP_MARGIN + yi * CELL_HEIGHT;

        // Year label
        ctx.fillStyle = "#666";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "right";
        ctx.fillText(String(year), LEFT_MARGIN - 6, y + CELL_HEIGHT - 2);

        // Draw cells
        const yearData = grid.get(year);
        for (let day = 0; day < 366; day++) {
          const cell = yearData?.get(day);
          const x = LEFT_MARGIN + day * CELL_WIDTH;

          ctx.fillStyle = tempToColor(getCellTemp(cell, tempType));
          ctx.fillRect(x, y, CELL_WIDTH, CELL_HEIGHT);
        }
      }
    },
    [canvasWidth, canvasHeight, years, endYear, tempType]
  );

  useEffect(() => {
    drawHeatmap(grid);
  }, [grid, drawHeatmap]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const day = Math.floor((x - LEFT_MARGIN) / CELL_WIDTH);
      const yearIdx = Math.floor((y - TOP_MARGIN) / CELL_HEIGHT);

      if (
        day < 0 ||
        day >= 366 ||
        yearIdx < 0 ||
        yearIdx >= years
      ) {
        setTooltip(null);
        return;
      }

      const year = endYear - yearIdx;
      const cell = grid.get(year)?.get(day);

      if (cell) {
        const d = new Date(cell.date);
        const dateStr = `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
        const temp = getCellTemp(cell, tempType);
        const tempStr =
          temp !== null ? `${temp.toFixed(1)}℃` : "データなし";
        const cursorX = e.clientX - rect.left;
        const alignRight = cursorX > canvasWidth / 2;
        setTooltip({
          x: alignRight ? cursorX - 10 : cursorX + 10,
          y: e.clientY - rect.top - 10,
          text: `${dateStr}: ${tempStr}`,
          alignRight,
        });
      } else {
        setTooltip(null);
      }
    },
    [grid, years, endYear, tempType, canvasWidth]
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div className="relative w-fit mx-auto">
      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="cursor-crosshair"
      />
      {tooltip && (
        <div
          className="pointer-events-none absolute rounded bg-black/80 px-2 py-1 text-xs text-white whitespace-nowrap"
          style={
            tooltip.alignRight
              ? { right: canvasWidth - tooltip.x, top: tooltip.y }
              : { left: tooltip.x, top: tooltip.y }
          }
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
