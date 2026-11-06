import assert from "node:assert/strict";
import test from "node:test";
import { ScatterTrail } from "./scatter-trail.ts";

const array = (values) => ({ dtype: "<f8", shape: [1, values.length], data: new Float64Array(values) });

test("trail bounds apply immediately without new samples or duplicate points", () => {
  const trail = new ScatterTrail();
  const values = Array.from({ length: 20 }, (_, i) => array([i, i]));
  for (const value of values) trail.update(value, true, 20);
  trail.update(values.at(-1), true, 10);
  assert.deepEqual(
    trail.points,
    values.slice(-10).map((value) => Array.from(value.data)),
  );
  trail.update(values.at(-1), true, 10);
  assert.equal(trail.points.length, 10);
});

test("calibration and dimension changes reset the trail; nonfinite samples are excluded", () => {
  const trail = new ScatterTrail();
  const value = array([1, 2]);
  trail.update(value, true, 10);
  trail.update(array([NaN, 2]), true, 10);
  trail.update(array([1, Infinity]), true, 10);
  assert.deepEqual(trail.points, [[1, 2]]);
  trail.update(value, false, 10);
  assert.deepEqual(trail.points, []);
  trail.update(value, true, 10);
  assert.deepEqual(trail.points, [[1, 2]]);
  trail.update(array([1, 2, 3]), true, 10);
  assert.deepEqual(trail.points, [[1, 2, 3]]);
});
