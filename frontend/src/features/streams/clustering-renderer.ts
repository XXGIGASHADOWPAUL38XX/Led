import type { ClusteringInput } from "../nodes/clustering.ts";
import { samples } from "./canvas-renderer.ts";

/** Alternating parameter axes cross within one centered grid. */
export function drawClustering(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  value: unknown,
  inputs: ClusteringInput[],
) {
  drawAxisGrid(ctx, width, height, samples(value), inputs.length);
}

/** Shared grid for linked parameters and higher-dimensional coordinates. */
export function drawAxisGrid(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  data: ArrayLike<number | bigint>,
  count: number,
) {
  ctx.clearRect(0, 0, width, height);
  ctx.font = "9px monospace";
  if (!count) {
    ctx.fillStyle = "#71717a";
    ctx.fillText("Add a parameter to begin", 8, 24);
    return;
  }
  const left = 24,
    right = width - 24,
    top = 24,
    bottom = height - 24;
  const horizontalCount = Math.ceil(count / 2),
    verticalCount = Math.floor(count / 2);
  const dots: { x: number; y: number; raw: number; vertical: boolean; color: string }[] = [];
  for (let index = 0; index < count; index++) {
    const vertical = index % 2 === 1,
      slot = Math.floor(index / 2) + 1;
    const color = vertical ? "#67e8f9" : "#c4b5fd";
    const fixedX = left + (slot * (right - left)) / (verticalCount + 1);
    const fixedY = top + (slot * (bottom - top)) / (horizontalCount + 1);
    ctx.strokeStyle = vertical ? "#67e8f933" : "#c4b5fd33";
    ctx.lineWidth = 1;
    ctx.beginPath();
    if (vertical) {
      ctx.moveTo(fixedX, top);
      ctx.lineTo(fixedX, bottom);
    } else {
      ctx.moveTo(left, fixedY);
      ctx.lineTo(right, fixedY);
    }
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.textAlign = vertical ? "center" : "left";
    ctx.fillText(String(index + 1), vertical ? fixedX : 6, vertical ? 13 : fixedY + 3);
    const raw = Number(data[index * 2]),
      position = Number(data[index * 2 + 1]);
    if (Number.isFinite(raw) && Number.isFinite(position))
      dots.push({
        x: vertical ? fixedX : left + position * (right - left),
        y: vertical ? bottom - position * (bottom - top) : fixedY,
        raw,
        vertical,
        color,
      });
  }
  for (const { x, y, raw, vertical, color } of dots) {
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, 2 * Math.PI);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.textAlign = vertical ? "left" : "center";
    ctx.fillText(Number(raw.toPrecision(5)).toString(), vertical ? x + 8 : x, vertical ? y + 3 : y - 8);
  }
}
