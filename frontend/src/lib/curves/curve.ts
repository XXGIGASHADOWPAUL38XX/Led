export type CurvePoint = readonly [number, number];
export type CurveValue = { points: CurvePoint[]; slopes: number[]; ids: string[] };
export type CurveAxis = "x" | "y" | "slope";
export const curvePort = (id: string, axis: CurveAxis) => `point_${id}_${axis}`;
export const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
export function curveY(start: CurvePoint, end: CurvePoint, slope: number, t: number) {
  t = clamp(t, 0, 1);
  return start[1] + (end[1] - start[1]) * (t - clamp(slope, -1, 1) * t * (1 - t));
}
export function curvePath(start: CurvePoint, end: CurvePoint, slope: number) {
  return Array.from({ length: 49 }, (_, i) => {
    const t = i / 48;
    return `${i ? "L" : "M"}${(start[0] + (end[0] - start[0]) * t) * 240},${(1 - curveY(start, end, slope, t)) * 120}`;
  }).join(" ");
}
