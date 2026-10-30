import test from 'node:test';
import assert from 'node:assert/strict';
import { arrayShape, parseArrayShape, parseNumericArray } from './array-values.ts';
import { compatiblePorts } from '../nodes/configuration.ts';

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

test('shape editor supports changing rank while validating dimensions', () => {
  assert.deepEqual(parseArrayShape('[180]'), [180]);
  assert.deepEqual(parseArrayShape('[180,3]'), [180,3]);
  for (const text of ['[]', '[0]', '[-1]', '[1.5]', '[[180,3]]', '[true]', '[65537]', '[65536,65536]']) assert.throws(() => parseArrayShape(text));
});

test('RGB requires a matching configured input shape', () => {
  assert.equal(compatiblePorts({ shape: [180,3] }, { shape: [180,3] }), true);
  assert.equal(compatiblePorts({ shape: [] }, { shape: [180] }), false);
  assert.equal(compatiblePorts({ shape: [180,3] }, { shape: [180] }), false);
  assert.equal(compatiblePorts({ shape: [2,2048] }, { shape: [2,0] }), true);
});
