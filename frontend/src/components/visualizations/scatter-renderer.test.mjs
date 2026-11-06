import assert from 'node:assert/strict';
import test from 'node:test';
import { drawScatter } from './scatter-renderer.ts';
import { drawClustering } from './clustering-renderer.ts';

function context() {
  return { dots: [], text: [], clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, save() {}, restore() {}, rect() {}, clip() {}, fill() {},
    arc(x, y) { this.dots.push([x, y]); }, fillText(text) { this.text.push(text); } };
}
const array = values => ({ dtype: '<f4', shape: [values.length], data: new Float32Array(values) });

test('scatter waits for calibration before drawing a point', () => {
  const ctx = context();
  drawScatter(ctx, 300, 300, array([0, 0]), array([.5, 0]), [], {});
  assert.equal(ctx.dots.length, 0);
  assert.ok(ctx.text.some(text => text.includes('50%')));
});

test('nonfinite live coordinates never reach canvas geometry', () => {
  for (const values of [[NaN, 1], [1, Infinity, 2], [1, 2, 3, NaN]]) {
    const ctx = context();
    drawScatter(ctx, 300, 300, array(values), array([1, 1]), [], {});
    assert.deepEqual(ctx.dots, []);
  }
});

test('scatter draws one live NMF point over its trail', () => {
  const ctx = context();
  drawScatter(ctx, 300, 300, array([1, 1]), array([1, 1]), [[0, 0], [1, 1]], { range: [0, 2] });
  assert.deepEqual(ctx.dots, [[158, 152]]);
  assert.ok(ctx.text.includes('NMF1') && ctx.text.includes('NMF2'));
});

test('XYZ uses depth and camera rotation without changing the coordinates', () => {
  const first = context(), depth = context(), rotated = context();
  const value = array([.2, .4, .6]);
  drawScatter(first, 300, 300, value, array([1, 1]), [], { range: [0, 1] }, [0, 0]);
  drawScatter(depth, 300, 300, array([.2, .4, .9]), array([1, 1]), [], { range: [0, 1] }, [0, 0]);
  drawScatter(rotated, 300, 300, value, array([1, 1]), [], { range: [0, 1] }, [1, .5]);
  assert.equal(first.dots.length, 1);
  assert.notDeepEqual(first.dots, depth.dots);
  assert.notDeepEqual(first.dots, rotated.dots);
  assert.ok(first.dots.flat().every(Number.isFinite));
  assert.ok(first.text.includes('Z') && first.text.some(label => label.includes('Drag to rotate')));
  assert.deepEqual(Array.from(value.data), Array.from(new Float32Array([.2, .4, .6])));
});

test('4D coordinates use exactly the Clustering grid with editable reversed ranges', () => {
  const scatter = context(), clustering = context();
  const value = { dtype: '<f8', shape: [1, 4], data: new Float64Array([.2, .4, .6, .8]) };
  drawScatter(scatter, 300, 300, value, array([1, 1]), [], { range: [0, 1], axisRanges: { 0: [0, .4], 2: [1, 0] } });
  drawClustering(clustering, 300, 300, { dtype: '<f8', shape: [4, 2], data: new Float64Array([.2, .5, .4, .4, .6, .4, .8, .8]) },
    Array.from({ length: 4 }, () => ({ source: null, interval: [0, 1] })));
  assert.deepEqual(scatter.dots, clustering.dots);
  assert.equal(scatter.dots.length, 4);
});
