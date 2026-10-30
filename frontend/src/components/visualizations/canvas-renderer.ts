import { isArrayValue } from "../../lib/backend/protocol.ts";
import type { ViewSettings } from "../../lib/backend/template.ts";
import type { ViewDefinition } from "../node/definition.ts";

export const palette = ["#a78bfa", "#38bdf8", "#34d399", "#fb7185", "#fbbf24", "#f472b6"];
export function rgba(channels: readonly number[]) {
  const [red, green, blue, alpha = 255] = channels;
  return `rgba(${red}, ${green}, ${blue}, ${alpha / 255})`;
}
export const seriesColor = (settings: ViewSettings, row: number) => settings.lineColors?.[row] ? rgba(settings.lineColors[row]) : palette[row % palette.length];
export function samples(value: unknown): ArrayLike<number | bigint> {
  if (isArrayValue(value)) return value.data;
  return typeof value === "number" || typeof value === "boolean" ? [Number(value)] : [];
}

/** Read typed arrays directly; drawing work is bounded by the canvas width. */
export function drawStream(ctx: CanvasRenderingContext2D, width: number, height: number,
  value: unknown, colors: unknown, view: ViewDefinition, settings: ViewSettings, history: readonly (readonly number[])[]) {
  const data = samples(value);
  const meter = view.kind === "meter";
  const count = meter ? history[0]?.length ?? 0 : view.kind === "history" && isArrayValue(value) ? value.shape.at(-1)! : data.length;
  const rows = meter ? view.series?.length ?? 1 : view.kind === "history" && isArrayValue(value) && value.shape.length > 1 ? Math.min(value.shape[0], 8) : 1;
  const sample = (row: number, index: number) => Number(meter ? history[row][index] : data[row * count + index]);
  ctx.clearRect(0, 0, width, height);
  ctx.font = "10px monospace";
  ctx.fillStyle = "#71717a";
  if (!count) { ctx.fillText(`Waiting for ${view.data}…`, 8, 24); return; }
  if (view.kind === "trigger") {
    ctx.fillStyle = Number(data[data.length - 1]) !== 0 ? "#34d399" : "#27272a";
    ctx.beginPath(); ctx.arc(16, 20, 6, 0, Math.PI * 2); ctx.fill();
    return;
  }
  if (view.kind === "color") {
    if (!isArrayValue(value)) return;
    const count = value.shape[0], channels = value.shape[1];
    const bars = Math.min(count, Math.ceil(width));
    for (let i = 0; i < bars; i++) {
      const at = Math.floor(i * count / bars) * channels;
      ctx.fillStyle = rgba(Array.from({ length: channels }, (_, c) => Number(data[at + c])));
      ctx.fillRect(i * width / bars, 0, width / bars + 0.5, height);
    }
    return;
  }
  const lines = view.kind === "history" || view.kind === "meter";
  const points = Math.min(count, Math.max(1, Math.floor(width - 36)));
  const index = (point: number) => Math.round(point * (count - 1) / Math.max(1, points - 1));
  let low = 0, high = 1;
  for (let row = 0; row < rows; row++) for (let p = 0; p < points; p++) {
    const n = sample(row, index(p));
    if (Number.isFinite(n)) { low = Math.min(low, n); high = Math.max(high, n); }
  }
  [low, high] = settings.range ?? (view.kind === "lights" && settings.range === undefined ? [0, 1] : [low, high]);
  const left = 32, top = view.kind === "meter" ? 28 : 8, bottom = height - 12;
  const plotWidth = Math.max(1, width - left - 4);
  const y = (n: number) => bottom - (n - low) / (high - low) * (bottom - top);
  for (let tick = 0; tick < 3; tick++) {
    const n = low + (high - low) * tick / 2;
    ctx.fillStyle = "#71717a"; ctx.fillText(Number(n.toPrecision(3)).toString(), 0, y(n) + 3);
    ctx.strokeStyle = "#ffffff0d"; ctx.beginPath(); ctx.moveTo(left, y(n)); ctx.lineTo(width, y(n)); ctx.stroke();
  }
  if (view.kind === "meter") {
    for (let row = 0; row < rows; row++) {
      ctx.fillStyle = seriesColor(settings, row);
      ctx.fillText(`${view.series ? `${view.series[row]} ` : ""}${sample(row, count - 1).toPrecision(4)} ${view.unit ?? ""}`, left + row * plotWidth / rows, 16);
    }
  }
  ctx.save(); ctx.beginPath(); ctx.rect(left, top, plotWidth, bottom - top); ctx.clip();
  if (lines) {
    for (let row = 0; row < rows; row++) {
      if (settings.hiddenSeries?.includes(String(row))) continue;
      ctx.strokeStyle = seriesColor(settings, row);
      ctx.lineWidth = 1.5; ctx.beginPath();
      let connected = false;
      for (let p = 0; p < points; p++) {
        const n = sample(row, index(p));
        if (!Number.isFinite(n)) { connected = false; continue; }
        const x = left + p * plotWidth / Math.max(1, points - 1);
        if (connected) ctx.lineTo(x, y(n)); else ctx.moveTo(x, y(n));
        connected = true;
      }
      ctx.stroke();
    }
  } else {
    const channels = isArrayValue(colors) && colors.shape[0] === count ? colors.shape[1] : 0;
    const colorData = samples(colors);
    const gradient = ctx.createLinearGradient(0, top, 0, bottom);
    gradient.addColorStop(0, "#c4b5fd"); gradient.addColorStop(1, "#7c3aed73");
    for (let p = 0; p < points; p++) {
      const at = index(p), n = Number(data[at]);
      if (!Number.isFinite(n)) continue;
      ctx.fillStyle = view.kind === "lights" && channels ? rgba(Array.from({ length: channels }, (_, c) => Number(colorData[at * channels + c]))) : gradient;
      ctx.fillRect(left + p * plotWidth / points, Math.min(y(n), y(0)), plotWidth / points, Math.abs(y(n) - y(0)));
    }
  }
  ctx.restore();
}
