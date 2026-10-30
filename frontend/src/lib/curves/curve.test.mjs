import assert from 'node:assert/strict';
import test from 'node:test';
import { curveY, curvePath, curvePort } from './curve.ts';

test('segment bends preserve endpoints, bounds and direction', () => {
  for (const [start, end] of [[[0, 0], [1, 1]], [[0.2, 0.9], [0.8, 0.1]]]) {
    for (const slope of [-1, -0.5, 0, 0.5, 1]) {
      assert.equal(curveY(start, end, slope, 0), start[1]);
      assert.ok(Math.abs(curveY(start, end, slope, 1) - end[1]) < 1e-12);
      const values = Array.from({ length: 101 }, (_, i) => curveY(start, end, slope, i / 100));
      assert.ok(values.every((value) => value >= Math.min(start[1], end[1]) - 1e-12 && value <= Math.max(start[1], end[1]) + 1e-12));
      assert.ok(values.slice(1).every((value, i) => (value - values[i]) * Math.sign(end[1] - start[1]) >= -1e-12));
      assert.ok(values.slice(1).every((value, i) => Math.abs(value - values[i]) <= Math.abs(end[1] - start[1]) * 0.02 + 1e-12));
      assert.ok(!curvePath(start, end, slope).includes('NaN'));
    }
  }
  assert.equal(curveY([0, 0], [1, 1], 0, 0.5), 0.5);
  assert.equal(curveY([0, 0], [1, 1], 0.5, 0.5), 0.375);
  assert.equal(curveY([0, 0], [1, 1], -0.5, 0.5), 0.625);
});

test('control names use persistent point identity rather than position', () => {
  const ids = ['left', 'right'];
  const before = curvePort(ids[1], 'y');
  ids.splice(1, 0, 'inserted');
  assert.equal(curvePort(ids[2], 'y'), before);
});
