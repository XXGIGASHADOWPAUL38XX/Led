import assert from 'node:assert/strict';
import test from 'node:test';
import { readExpression, writeExpression } from './operator-expression.ts';
const a = { nodeId: 'bass', element: 'data' };
const b = { nodeId: 'highs', element: 'data' };

test('legacy tokens become a compact expression and retain repeated source identity', () => {
  const state = readExpression(['(', a, '+', b, ')', '/', a], [], [null, 'bass:data', null, 'highs:data']);
  assert.equal(state.expression, '( v0 + v1 ) / v0');
  assert.deepEqual(state.inputs.map((input) => input.port), ['bass:data', 'highs:data']);
  const result = writeExpression('clip(v0 + v1 * 1e-3, 0, 1)', state.inputs);
  assert.deepEqual(result.arguments, ['clip(', a, '+', b, '* 1e-3, 0, 1)']);
  assert.deepEqual(result.input_names, ['v0', 'v1']);
  assert.equal(readExpression(result.arguments, result.input_names).expression, 'clip( v0 + v1 * 1e-3, 0, 1)');
});

test('renamed inputs persist, remove unused bindings and reject conflicting names', () => {
  const inputs = [{ name: 'bass', value: a }, { name: 'highs', value: b }];
  assert.deepEqual(writeExpression('bass * 2', inputs), { arguments: [a, '* 2'], input_names: ['bass'] });
  assert.throws(() => writeExpression('clip', [{ name: 'clip', value: a }]), /unique identifiers/);
  assert.throws(() => writeExpression('x', [{ name: 'x', value: a }, { name: 'x', value: b }]), /unique identifiers/);
});

test('several expressions share input names and keep references used only by extra outputs', async () => {
  const { readExpressions, writeExpressions } = await import('./operator-expression.ts');
  const draft = readExpressions([a, '* 2'], [{ name: 'difference', arguments: [b, '-', a] }], ['bass', 'highs'], ['bass:data', null, 'highs:data', null, null]);
  assert.equal(draft.inputs.length, 2);
  assert.deepEqual(draft.outputs, [{ name: 'data', expression: 'bass * 2' }, { name: 'difference', expression: 'highs - bass' }]);
  const saved = writeExpressions(draft.outputs, draft.inputs);
  assert.deepEqual(saved.operations, [{ name: 'difference', arguments: [b, '-', a] }]);
  assert.deepEqual(saved.input_names, ['bass', 'highs']);
  assert.throws(() => writeExpressions([{ name: 'data', expression: '1' }, { name: 'data', expression: '2' }], []), /unique identifiers/);
});
