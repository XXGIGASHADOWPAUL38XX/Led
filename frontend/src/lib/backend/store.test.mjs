import test from 'node:test';
import assert from 'node:assert/strict';
import { BackendStore } from './store.ts';

const descriptor = (value) => ({ id: 'amp', type: 'Amplitudes', elements: [{ name: 'powering', value }], ports: [{ name: 'data', direction: 'out' }] });
function setup() {
  const store = new BackendStore();
  store.connection.send = () => {};
  store.receive({ type: 'graph.snapshot', revision: 1, payload: { graph: { nodes: [], connections: [] }, nodes: [descriptor(0.5)], catalog: [] } });
  return store;
}

test('frames notify only the subscribed array, not graph or controls', () => {
  const store = setup();
  let graphs = 0, controls = 0, arrays = 0;
  store.subscribe('graph', () => graphs++);
  store.subscribe('node:amp', () => controls++);
  store.watchArray('amp', 'data', () => arrays++);
  store.receive({ type: 'frame', revision: 1, payload: { sequence: 1, values: [{ nodeId: 'amp', element: 'data', value: { dtype: '<f4', shape: [1], data: new Float32Array([1]) } }], players: [] } });
  assert.equal(graphs, 0);
  assert.equal(controls, 0);
  assert.equal(arrays, 1);
});

test('an older edit response cannot overwrite a newer optimistic value', async () => {
  const store = setup();
  const resolve = [];
  store.connection.request = () => new Promise((done) => resolve.push(done));
  const first = store.setElement('amp', 'powering', 0.75);
  const second = store.setElement('amp', 'powering', 1);
  store.receive({ type: 'state.update', revision: 2, payload: { node: descriptor(0.75) } });
  resolve[0]({ value: 0.75 });
  await first;
  assert.equal(store.node('amp').elements[0].value, 1);
  store.receive({ type: 'state.update', revision: 3, payload: { node: descriptor(1) } });
  resolve[1]({ value: 1 });
  await second;
  assert.equal(store.node('amp').elements[0].value, 1);
});

test('rejected edits restore authoritative state and expose the error', async () => {
  const store = setup();
  store.connection.request = async () => { throw Error('Out of range'); };
  await store.setElement('amp', 'powering', 100);
  assert.equal(store.node('amp').elements[0].value, 0.5);
  assert.equal(store.status.error, 'Out of range');
});

test('batched positions update the graph once and preserve streamed data', () => {
  const store = setup();
  store.snapshot.graph.nodes = ['amp', 'buffer'].map(id => ({ id, position: [0, 0] }));
  const value = { dtype: '<f4', shape: [1], data: new Float32Array([1]) };
  store.receive({ type: 'frame', revision: 1, payload: { sequence: 1, values: [{ nodeId: 'amp', element: 'data', value }], players: [] } });
  let updates = 0;
  store.subscribe('graph', () => updates++);
  store.receive({ type: 'state.update', revision: 2, payload: { positions: { amp: [400, 24], buffer: [24, 24] } } });
  assert.equal(updates, 1);
  assert.deepEqual(store.snapshot.graph.nodes.map(node => node.position), [[400, 24], [24, 24]]);
  assert.equal(store.array('amp', 'data'), value);
});
