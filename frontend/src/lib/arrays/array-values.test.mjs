import test from 'node:test';
import assert from 'node:assert/strict';
import { arrayShape, parseNumericArray } from './array-values.ts';

test('accepts bounded arrays without changing dimensions or integer constraints', () => {
  assert.deepEqual(parseNumericArray('[[1,2],[3,4]]', [[0,0],[0,0]], { integer: true, min: 0, max: 4 }), [[1,2],[3,4]]);
  assert.deepEqual(arrayShape([[[1,2]],[[3,4]]]), [2,1,2]);
  assert.deepEqual(parseNumericArray('[]', []), []);
});

test('rejects malformed, ragged, nonnumeric and nonfinite arrays', () => {
  for (const text of ['[', '1', '[[1],[2,3]]', '["1",2]', '[null,2]', '[1e999,2]', '[{},2]']) {
    assert.throws(() => parseNumericArray(text, [0,0]), undefined, text);
  }
});

test('rejects resized arrays, values outside bounds and fractional integers', () => {
  assert.throws(() => parseNumericArray('[1,2,3]', [0,0]));
  assert.throws(() => parseNumericArray('[1,20]', [0,0], { max: 10 }));
  assert.throws(() => parseNumericArray('[-1,0]', [0,0], { min: 0 }));
  assert.throws(() => parseNumericArray('[1,1.5]', [0,0], { integer: true }));
});
