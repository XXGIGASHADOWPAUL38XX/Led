import assert from 'node:assert/strict';
import test from 'node:test';
import { availableNodeName } from './node-name.ts';

test('automatic node names are readable and avoid every existing ID', () => {
  assert.equal(availableNodeName('Value Transformer', []), 'Value Transformer');
  assert.equal(availableNodeName('Value Transformer', ['Value Transformer']), 'Value Transformer 2');
  assert.equal(availableNodeName('Value Transformer', ['Value Transformer', 'Value Transformer 2', 'Value Transformer 4']), 'Value Transformer 3');
  assert.equal(availableNodeName('Gradiant', ['Value Transformer']), 'Gradiant');
});
