import type { ArrayValue } from "../../api/protocol.ts";

/** Keep stream history independent of React renders and display settings. */
export class ScatterTrail {
  readonly points: number[][] = [];
  private previous: ArrayValue | null = null;

  update(value: ArrayValue | null, ready: boolean, limit: number) {
    if (!ready) {
      this.points.length = 0;
      this.previous = null;
      return;
    }
    if (value !== null && value !== this.previous) {
      const point = Array.from(value.data, Number);
      if (this.points[0]?.length !== point.length) this.points.length = 0;
      if (point.length >= 2 && point.every(Number.isFinite)) this.points.push(point);
      this.previous = value;
    }
    this.points.splice(0, Math.max(0, this.points.length - limit));
  }
}
