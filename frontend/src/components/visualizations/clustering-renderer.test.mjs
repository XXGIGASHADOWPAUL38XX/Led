import assert from 'node:assert/strict';
import test from 'node:test';
import { drawClustering } from './clustering-renderer.ts';

function context() {
  return { dots: [], labels: [], lines: [], clearRect() {}, beginPath() {}, moveTo(x, y) { this.start = [x, y]; }, lineTo(x, y) { this.lines.push([...this.start, x, y]); }, stroke() {}, fill() {},
    arc(x, y) { this.dots.push([x, y]); }, fillText(text) { this.labels.push(text); } };
}

test('alternating axes cross in one grid and retain independent live dots', () => {
  const ctx = context();
  const inputs = ['RMS', 'Frequency', 'Entropy', 'Flux'].map(nodeId => ({ source: { nodeId, element: 'data' }, interval: [0, 1] }));
  drawClustering(ctx, 300, 300, { dtype: '<f4', shape: [4, 2], data: new Float32Array([.5, .5, 2, .75, -1, 0, 1, 1]) }, inputs);
  assert.deepEqual(ctx.lines, [[24, 108, 276, 108], [108, 24, 108, 276], [24, 192, 276, 192], [192, 24, 192, 276]]);
  assert.deepEqual(ctx.dots, [[150, 108], [108, 87], [24, 192], [192, 24]]);
  for (const value of ['0.5', '2', '-1']) assert.ok(ctx.labels.includes(value));
});

test('waiting data draws no invalid dots', () => {
  const ctx = context();
  drawClustering(ctx, 300, 72, null, [{ source: null, interval: [0, 1] }]);
  assert.equal(ctx.dots.length, 0);
});
