import assert from 'node:assert/strict';
import test from 'node:test';
import { drawAngle } from './angle-renderer.ts';

test('angles retain a constant radius in every quadrant on a rectangular canvas', () => {
  const arcs = [];
  const ctx = { clearRect() {}, fillText() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, fill() {},
    arc(x, y, radius) { arcs.push([x, y, radius]); } };
  const value = { dtype: '<f8', shape: [5], data: new Float64Array([0, Math.PI / 2, Math.PI, -Math.PI / 2, Math.PI / 4]) };
  drawAngle(ctx, 400, 300, value);
  const [cx, cy, radius] = arcs[0];
  assert.equal(arcs.length, 6);
  for (const [x, y] of arcs.slice(1)) assert.ok(Math.abs(Math.hypot(x - cx, y - cy) - radius) < 1e-10);
  assert.ok(arcs[1][0] > cx && arcs[2][1] < cy && arcs[3][0] < cx && arcs[4][1] > cy);
});
