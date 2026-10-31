import test from 'node:test';
import assert from 'node:assert/strict';
import { compatibleTerminals, terminalKey } from './terminal-compatibility.ts';

const nodes = [
  { id: 'source', ports: [{ name: 'data', direction: 'out', shape: [4] }, { name: 'self', direction: 'in', shape: [4] }] },
  { id: 'target', ports: [
    { name: 'same', direction: 'in', shape: [4] },
    { name: 'wrong', direction: 'in', shape: [2, 4] },
    { name: 'adaptive', direction: 'in', shape: [2, 2048], adaptiveShape: true },
    { name: 'add', direction: 'in', shape: [], variadic: true },
    { name: 'output', direction: 'out', shape: [4] },
  ] },
];
test('drag highlights matching, adaptive, and append inputs while excluding self and outputs', () => {
  const keys = compatibleTerminals(nodes, { nodeId: 'source', element: 'data' }, 'output');
  assert.deepEqual([...keys], ['same', 'adaptive', 'add'].map((element) => terminalKey({ nodeId: 'target', element }, 'input')));
});
test('reverse dragging finds outputs and an absent source produces no highlights', () => {
  assert.deepEqual([...compatibleTerminals(nodes, { nodeId: 'target', element: 'same' }, 'input')], [terminalKey({ nodeId: 'source', element: 'data' }, 'output')]);
  assert.equal(compatibleTerminals(nodes, { nodeId: 'missing', element: 'data' }, 'output').size, 0);
});
