import assert from 'node:assert/strict';
import test from 'node:test';
import { drawStream, samples } from './canvas-renderer.ts';

const array = (shape, data) => ({ dtype: '<f4', shape, data: new Float32Array(data) });
function context() {
  const rectangles = [], paths = [];
  return {
    rectangles, paths, clearRect() {}, fillText() {}, beginPath() {}, moveTo() {},
    lineTo(x, y) { paths.push([x, y]); }, stroke() {}, save() {}, restore() {}, rect() {}, clip() {},
    fillRect(...rect) { rectangles.push({ color: this.fillStyle, rect }); },
    createLinearGradient() { return { addColorStop() {} }; },
  };
}

test('180 lights keep equal heights and independent RGBA alpha', () => {
  const ctx = context();
  const colors = array([180, 4], Array.from({ length: 180 }, (_, i) => [255, 0, 128, i]).flat());
  drawStream(ctx, 300, 144, array([180], new Array(180).fill(1)), colors, { kind: 'lights', data: 'data' }, {}, []);
  assert.equal(ctx.rectangles.length, 180);
  assert.equal(new Set(ctx.rectangles.map(({ rect }) => rect[3])).size, 1);
  assert.equal(ctx.rectangles[0].color, 'rgba(255, 0, 128, 0)');
  assert.equal(ctx.rectangles[179].color, `rgba(255, 0, 128, ${179 / 255})`);
});

test('large arrays are read without copying and drawing is bounded by canvas width', () => {
  const ctx = context(), value = array([100000], new Float32Array(100000));
  assert.equal(samples(value), value.data);
  drawStream(ctx, 300, 144, value, null, { kind: 'bars' }, {}, []);
  assert.ok(ctx.rectangles.length <= 300);
});

test('history respects hidden channels and skips nonfinite points', () => {
  const ctx = context();
  drawStream(ctx, 300, 144, array([2, 3], [1, 2, 3, 4, NaN, 6]), null,
    { kind: 'history' }, { hiddenSeries: ['0'] }, []);
  assert.equal(ctx.paths.length, 3); // Grid only: the remaining channel has disconnected points.
  assert.ok(ctx.paths.flat().every(Number.isFinite));
});
