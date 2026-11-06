import { samples } from "./canvas-renderer.ts";

/** Equal X/Y scale keeps every displayed direction exactly one unit out. */
export function drawAngle(ctx: CanvasRenderingContext2D, width: number, height: number, value: unknown) {
  ctx.clearRect(0, 0, width, height);
  const cx = width / 2,
    cy = height / 2 + 6;
  const radius = Math.max(1, Math.min(width - 64, height - 76) / 2);
  ctx.font = "10px monospace";
  ctx.textAlign = "center";
  ctx.fillStyle = "#a1a1aa";
  ctx.fillText("90°", cx, cy - radius - 10);
  ctx.fillText("−90°", cx, cy + radius + 16);
  ctx.fillText("180°", cx - radius - 18, cy + 3);
  ctx.fillText("0°", cx + radius + 14, cy + 3);
  ctx.strokeStyle = "#ffffff18";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx - radius, cy);
  ctx.lineTo(cx + radius, cy);
  ctx.moveTo(cx, cy - radius);
  ctx.lineTo(cx, cy + radius);
  ctx.stroke();
  ctx.strokeStyle = "#a78bfa60";
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
  ctx.stroke();
  const angles = Array.from(samples(value), Number);
  ctx.fillText(
    angles
      .slice(0, 3)
      .map((a) => `${a.toFixed(3)} rad`)
      .join(" · ") + (angles.length > 3 ? " …" : ""),
    cx,
    14,
  );
  for (let i = 0; i < angles.length; i++) {
    if (!Number.isFinite(angles[i])) continue;
    const x = cx + Math.cos(angles[i]) * radius,
      y = cy - Math.sin(angles[i]) * radius;
    const color = `hsl(${185 + i * 137.5} 85% 70%)`;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, 2 * Math.PI);
    ctx.fill();
  }
}
