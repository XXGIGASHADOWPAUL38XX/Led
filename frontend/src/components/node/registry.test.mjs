import assert from 'node:assert/strict';
import test from 'node:test';
import { nodeDefinitions } from './registry.ts';
import { completeConfiguration, compatiblePorts } from '../../lib/nodes/configuration.ts';

test('each node definition covers unique controls and existing visual outputs', () => {
  assert.equal(Object.keys(nodeDefinitions).length, 66);
  for (const [type, node] of Object.entries(nodeDefinitions)) {
    assert.equal(node.type, type);
    assert.ok(node.description && node.category && node.title);
    assert.equal(new Set(node.fields.map((field) => field.name)).size, node.fields.length);
    assert.ok(node.views.every((view) => view.kind === 'playlist' || view.data));
  }
  assert.equal(nodeDefinitions.Function.fields.find((field) => field.name === 'points').control, 'curve');
  assert.equal(nodeDefinitions.OperatorPipeline.fields.find((field) => field.name === 'arguments').item, 'token');
  assert.equal(nodeDefinitions.AveragedWindowFct.fields.find((field) => field.name === 'avg_axis').control, 'axis');
});

test('unfinished references cannot be applied; literals and completed references can', () => {
  const fields = nodeDefinitions.OperatorPipeline.fields;
  assert.equal(completeConfiguration(fields, { arguments: [null, '*', 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{}, '*', 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{ nodeId: 'a' }, '*', 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{ nodeId: 'a', element: 'data' }, '*', 1] }), true);
  assert.equal(completeConfiguration(nodeDefinitions.GroupNode.fields, { nodes: [{ nodeId: 'a' }] }), true);
});

test('connection choices exclude incompatible array ranks and fixed dimensions', () => {
  assert.equal(compatiblePorts({ shape: [2, 2048] }, { shape: [2, 2048] }), true);
  assert.equal(compatiblePorts({ shape: [180] }, { shape: [0] }), true);
  assert.equal(compatiblePorts({ shape: [2, 100] }, { shape: [2, 335] }), false);
  assert.equal(compatiblePorts({ shape: [180, 4] }, { shape: [180] }), false);
  assert.equal(compatiblePorts({ shape: [335] }, { shape: [2, 2048], adaptiveShape: true }), true);
  assert.equal(compatiblePorts({ shape: [4, 335] }, { shape: [2, 2048], adaptiveShape: true }), true);
  assert.equal(compatiblePorts({ shape: [] }, { shape: [2, 2048], adaptiveShape: true }), false);
  assert.equal(compatiblePorts({ shape: [2, 0] }, { shape: [2, 2048], adaptiveShape: true }), false);
});
