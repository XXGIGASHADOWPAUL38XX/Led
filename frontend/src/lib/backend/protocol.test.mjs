import test from 'node:test';
import assert from 'node:assert/strict';
import { encode } from '@msgpack/msgpack';
import { decodeMessage, encodeMessage } from './protocol.ts';

test('controls and arrays use the same MessagePack envelope', () => {
  const control = { type: 'element.set', requestId: 9, payload: { nodeId: 'amp', element: 'powering', value: 0.75 } };
  assert.deepEqual(decodeMessage(encodeMessage(control)), control);
  const array = { dtype: '<f4', shape: [2, 2], data: new Float32Array([1,2,3,4]) };
  const result = decodeMessage(encodeMessage({ type: 'frame', revision: 4, payload: { array } }));
  assert.deepEqual(result.payload.array.shape, [2,2]);
  assert.deepEqual([...result.payload.array.data], [1,2,3,4]);
  assert(result.payload.array.data instanceof Float32Array);
});

test('decodes unaligned binary, scalar, empty and int64 arrays', () => {
  for (const array of [
    { dtype: '<f8', shape: [], data: new Float64Array([1.5]) },
    { dtype: '<i8', shape: [2], data: new BigInt64Array([1n, 9007199254740993n]) },
    { dtype: '<f4', shape: [0,2], data: new Float32Array(0) },
  ]) {
    const result = decodeMessage(encodeMessage({ type: 'frame', payload: { longKeyCausesDifferentAlignment: array } }));
    assert.deepEqual(result.payload.longKeyCausesDifferentAlignment.shape, array.shape);
    assert.deepEqual([...result.payload.longKeyCausesDifferentAlignment.data], [...array.data]);
  }
});

test('rejects malformed array descriptors', () => {
  for (const descriptor of [
    { dtype: '|O', shape: [1], data: new Uint8Array(8) },
    { dtype: '<f4', shape: [-1], data: new Uint8Array(0) },
    { dtype: '<f4', shape: [100], data: new Uint8Array(4) },
  ]) assert.throws(() => decodeMessage(encode({ type: 'frame', payload: { array: { __ndarray__: true, ...descriptor } } })));
});
