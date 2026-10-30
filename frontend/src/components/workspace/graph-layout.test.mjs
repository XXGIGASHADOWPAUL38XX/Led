import assert from 'node:assert/strict';
import test from 'node:test';
import { layoutGraph } from './graph-layout.ts';

test('layout separates measured nodes, keeps edges left-to-right, and is deterministic', () => {
  const graph = {
    nodes: ['input', 'a', 'b', 'output', 'isolated'].map(id => ({ id, position: [0, 0] })),
    connections: [['input', 'a'], ['input', 'b'], ['a', 'output'], ['b', 'output']].map(([from, to]) => ({ source: { nodeId: from }, target: { nodeId: to } })),
  };
  const sizes = new Map(graph.nodes.map(({ id }, i) => [id, { width: 288, height: 100 + i * 250 }]));
  const original = structuredClone({ graph, sizes });
  const positions = layoutGraph(graph, sizes);
  assert.deepEqual(positions, layoutGraph(graph, sizes));
  assert.deepEqual({ graph, sizes }, original);
  for (const edge of graph.connections) assert.ok(positions[edge.source.nodeId][0] + 288 < positions[edge.target.nodeId][0]);
  for (let i = 0; i < graph.nodes.length; i++) {
    const a = graph.nodes[i].id, [ax, ay] = positions[a], sa = sizes.get(a);
    assert.ok(ax >= 0 && ay >= 0);
    for (const { id: b } of graph.nodes.slice(i + 1)) {
      const [bx, by] = positions[b], sb = sizes.get(b);
      assert.ok(ax + sa.width <= bx || bx + sb.width <= ax || ay + sa.height <= by || by + sb.height <= ay);
    }
  }
});

test('empty layouts do not create placeholder nodes', () => {
  assert.deepEqual(layoutGraph({ nodes: [], connections: [] }, new Map()), {});
});
