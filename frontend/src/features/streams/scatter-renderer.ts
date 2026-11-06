import type { ViewSettings } from "../../api/template.ts";
import { samples } from "./canvas-renderer.ts";
import { drawAxisGrid } from "./clustering-renderer.ts";

type Project = (point: readonly number[]) => readonly [number, number];

function drawTrail(
  ctx: CanvasRenderingContext2D,
  point: readonly number[],
  history: readonly (readonly number[])[],
  project: Project,
) {
  for (let i = 1; i < history.length; i++) {
    ctx.strokeStyle = `rgba(167,139,250,${(0.6 * i) / history.length})`;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(...project(history[i - 1]));
    ctx.lineTo(...project(history[i]));
    ctx.stroke();
  }
  if (point.every(Number.isFinite)) {
    ctx.fillStyle = "#67e8f9";
    ctx.shadowColor = "#67e8f9";
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(...project(point), 4, 0, 2 * Math.PI);
    ctx.fill();
  }
}

function drawXYZ(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  point: number[],
  history: readonly (readonly number[])[],
  low: number,
  high: number,
  [yaw, pitch]: readonly number[],
) {
  const size = Math.max(1, Math.min(width - 64, height - 90)) * 0.75;
  const project: Project = (value) => {
    const [x, y, z] = value.map((n) => (n - low) / (high - low) - 0.5);
    const horizontal = Math.cos(yaw) * x - Math.sin(yaw) * z;
    const depth = Math.sin(yaw) * x + Math.cos(yaw) * z;
    const vertical = Math.cos(pitch) * y - Math.sin(pitch) * depth;
    const perspective = 2.8 / (2.8 - Math.sin(pitch) * y - Math.cos(pitch) * depth);
    return [width / 2 + horizontal * size * perspective, height / 2 + 6 - vertical * size * perspective];
  };
  const corners = Array.from({ length: 8 }, (_, index) => [0, 1, 2].map((axis) => (index & (1 << axis) ? high : low)));
  ctx.strokeStyle = "#ffffff18";
  ctx.lineWidth = 1;
  for (let i = 0; i < 8; i++)
    for (let axis = 0; axis < 3; axis++) {
      const other = i ^ (1 << axis);
      if (other <= i) continue;
      ctx.beginPath();
      ctx.moveTo(...project(corners[i]));
      ctx.lineTo(...project(corners[other]));
      ctx.stroke();
    }
  for (let axis = 0; axis < 3; axis++) {
    const end = [low, low, low];
    end[axis] = high;
    const color = ["#fb7185", "#34d399", "#67e8f9"][axis];
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(...project([low, low, low]));
    ctx.lineTo(...project(end));
    ctx.stroke();
    const [x, y] = project(end);
    ctx.fillText(["X", "Y", "Z"][axis], x + 5, y - 5);
  }
  ctx.fillStyle = "#71717a";
  ctx.fillText("Drag to rotate · XYZ", 12, height - 8);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 22, width, height - 44);
  ctx.clip();
  drawTrail(ctx, point, history, project);
  ctx.restore();
}

export function drawScatter(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  value: unknown,
  status: unknown,
  history: readonly (readonly number[])[],
  settings: ViewSettings,
  camera: readonly number[] = [-0.7, 0.45],
) {
  ctx.clearRect(0, 0, width, height);
  ctx.font = "10px monospace";
  ctx.textAlign = "left";
  ctx.fillStyle = "#a1a1aa";
  const calibration = samples(status);
  if (Number(calibration[1]) !== 1) {
    const progress = Math.round(Number(calibration[0] ?? 0) * 100);
    ctx.fillText(progress === 100 ? "Fitting NMF…" : `Calibration ${progress}% · play audio`, 12, 26);
    return;
  }
  const point = Array.from(samples(value), Number);
  if (point.length < 2 || !point.every(Number.isFinite)) return;
  if (point.length > 3) {
    const values = point.flatMap((raw, index) => {
      let high = Math.max(1, raw);
      for (const previous of history) high = Math.max(high, previous[index] ?? 0);
      const [low, end] = settings.axisRanges?.[String(index)] ?? settings.range ?? [0, high * 1.05];
      return [raw, Math.min(1, Math.max(0, (raw - low) / (end - low)))];
    });
    drawAxisGrid(ctx, width, height, values, point.length);
    return;
  }
  const extent = Math.max(1, ...point, ...history.flat());
  const [low, high] = settings.range ?? [0, extent * 1.05];
  const left = 28,
    right = width - 12,
    top = 28,
    bottom = height - 24;
  const x = (n: number) => left + ((n - low) / (high - low)) * (right - left);
  const y = (n: number) => bottom - ((n - low) / (high - low)) * (bottom - top);
  ctx.fillText(point.map((n, index) => `${["X", "Y", "Z"][index]} ${n.toFixed(2)}`).join("  "), left, 14);
  if (point.length === 3) {
    drawXYZ(ctx, width, height, point, history, low, high, camera);
    return;
  }
  for (let i = 0; i < 5; i++) {
    const n = low + ((high - low) * i) / 4;
    ctx.strokeStyle = Math.abs(n) < 1e-9 ? "#ffffff40" : "#ffffff10";
    ctx.beginPath();
    ctx.moveTo(x(n), top);
    ctx.lineTo(x(n), bottom);
    ctx.moveTo(left, y(n));
    ctx.lineTo(right, y(n));
    ctx.stroke();
    ctx.fillText(Number(n.toPrecision(2)).toString(), 0, y(n) + 3);
  }
  ctx.fillText("NMF1", (left + right) / 2 - 10, height - 6);
  ctx.fillText("NMF2", 0, 14);
  ctx.save();
  ctx.beginPath();
  ctx.rect(left, top, right - left, bottom - top);
  ctx.clip();
  drawTrail(ctx, point, history, (p) => [x(p[0]), y(p[1])]);
  ctx.restore();
}
