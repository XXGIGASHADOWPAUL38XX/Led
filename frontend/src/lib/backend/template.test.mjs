import test from 'node:test';
import assert from 'node:assert/strict';
import { encodeMessage } from './protocol.ts';
import { encodeTemplate, decodeTemplate, viewKey } from './template.ts';
import { BackendStore } from './store.ts';

const graph = () => ({ nodes: [{ id: 'curve', type: 'Function', position: [125, -30], parameters: {
  points: { dtype: '<f4', shape: [2, 2], data: new Float32Array([0, 0, 1, 1]) },
} }], connections: [] });
const settings = { open: false, title: 'My spectrum', range: [0, 42], historyLength: 250,
  lineColors: { 0: [12, 34, 56, 128] }, hiddenSeries: ['1'], expanded: false };
const template = () => ({ version: 1, graph: graph(), ui: { curve: { [viewKey('history', 'data')]: structuredClone(settings) } } });
function snapshot(store, value) {
  store.receive({ type: 'graph.snapshot', revision: 1, payload: { graph: value,
    nodes: value.nodes.map((node) => ({ id: node.id, type: node.type, elements: [], ports: [] })), catalog: [] } });
}

test('templates preserve positions, dtype, shape, and all display settings', () => {
  const original = template();
  const restored = decodeTemplate(encodeTemplate(original));
  assert.deepEqual(restored, original);
  assert.ok(restored.graph.nodes[0].parameters.points.data instanceof Float32Array);
  original.graph.nodes[0].parameters.points = { dtype: '<i8', shape: [1], data: new BigInt64Array([9007199254740993n]) };
  assert.equal(decodeTemplate(encodeTemplate(original)).graph.nodes[0].parameters.points.data[0], 9007199254740993n);
});

test('bad versions, files, graphs, and display settings are rejected', () => {
  const pack = (value) => encodeMessage({ type: 'template', payload: value });
  for (const invalid of [
    { ...template(), version: 2 },
    { ...template(), graph: { nodes: 'bad', connections: [] } },
    { ...template(), ui: { curve: { chart: { range: [4, 1] } } } },
    { ...template(), ui: { curve: { chart: { historyLength: 1e9 } } } },
    { ...template(), ui: { curve: { chart: { lineColors: { 0: [999, 0, 0] } } } } },
    { ...template(), ui: { missing: {} } },
  ]) assert.throws(() => decodeTemplate(pack(invalid)));
  assert.throws(() => decodeTemplate(encodeMessage({ type: 'frame', payload: {} })), /template file/);
  assert.throws(() => decodeTemplate(new Uint8Array([0xc1])));
});

test('saving gets current Python values instead of a stale frontend graph', async () => {
  const store = new BackendStore();
  snapshot(store, { nodes: [], connections: [] });
  const fresh = graph();
  fresh.nodes[0].position = [200, 300];
  store.connection.request = async (type) => { assert.equal(type, 'graph.get'); return { graph: fresh }; };
  const saved = decodeTemplate(await store.exportTemplate());
  assert.deepEqual(saved.graph.nodes[0].position, [200, 300]);
  assert.equal(saved.graph.nodes[0].parameters.points.data.length, 4);
  assert.equal(Object.hasOwn(saved, 'players'), false);
});

test('display restoration waits for acceptance and notifies relevant views', async () => {
  const store = new BackendStore();
  const key = viewKey('history', 'data');
  snapshot(store, graph());
  store.setViewSettings('curve', key, { title: 'Current' });
  let resolve;
  store.connection.request = async (type, payload) => {
    assert.equal(type, 'graph.load'); assert.deepEqual(payload.graph, graph());
    return new Promise((done) => { resolve = done; });
  };
  let updates = 0, resets = 0, frames = 0;
  store.subscribe(`display:${JSON.stringify(['curve', key])}`, () => updates++);
  store.subscribe('template', () => resets++);
  store.subscribe('array:other', () => frames++);
  const pending = store.importTemplate(encodeTemplate(template()));
  assert.equal(store.viewSettings('curve', key).title, 'Current');
  resolve({ revision: 2 });
  await pending;
  assert.deepEqual(store.viewSettings('curve', key), settings);
  assert.equal(updates, 1); assert.equal(resets, 1); assert.equal(frames, 0);
  assert.equal(store.templateRevision, 1);
});

test('failed imports preserve display state; malformed files never reach Python', async () => {
  const store = new BackendStore();
  const key = viewKey('history', 'data');
  snapshot(store, graph());
  store.setViewSettings('curve', key, { title: 'Keep me' });
  let requests = 0;
  store.connection.request = async () => { requests++; throw Error('Unknown node'); };
  await assert.rejects(store.importTemplate(encodeTemplate(template())), /Unknown node/);
  assert.equal(store.viewSettings('curve', key).title, 'Keep me');
  assert.equal(store.templateRevision, 0);
  await assert.rejects(store.importTemplate(new Uint8Array([0xc1])));
  assert.equal(requests, 1);
});

test('view settings survive refreshes and are removed with deleted nodes', () => {
  const store = new BackendStore();
  const key = viewKey('bars', 'data');
  snapshot(store, graph());
  store.setViewSettings('curve', key, { open: false });
  snapshot(store, graph());
  assert.equal(store.viewSettings('curve', key).open, false);
  snapshot(store, { nodes: [], connections: [] });
  assert.deepEqual(store.viewSettings('curve', key), {});
});
