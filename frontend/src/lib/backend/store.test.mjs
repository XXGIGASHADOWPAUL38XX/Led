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

test('frame listeners see data and calibration from the same complete frame', () => {
  const store = setup();
  const value = { dtype: '<f4', shape: [2], data: new Float32Array([1, 2]) };
  const calibration = { dtype: '<f4', shape: [2], data: new Float32Array([1, 1]) };
  let notifications = 0;
  store.watchArray('amp', 'data', () => {
    notifications++;
    assert.equal(store.array('amp', 'data'), value);
    assert.equal(store.array('amp', 'calibration'), calibration);
  });
  store.receive({ type: 'frame', revision: 1, payload: { sequence: 1, values: [
    { nodeId: 'amp', element: 'data', value },
    { nodeId: 'amp', element: 'calibration', value: calibration },
  ], players: [] } });
  assert.equal(notifications, 1);
});

test('repeated cleanup cannot remove a replacement listener', () => {
  const store = setup();
  const off = store.subscribe('status', () => {});
  off();
  let calls = 0;
  store.subscribe('status', () => calls++);
  off();
  store.receive({ type: 'ack', revision: 2, payload: {} });
  assert.equal(calls, 1);
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

test('same-revision acknowledgements do not trigger workspace rerenders', () => {
  const store = setup();
  let notifications = 0;
  store.subscribe('status', () => notifications++);
  store.receive({ type: 'ack', revision: 1, payload: {} });
  assert.equal(notifications, 0);
  store.receive({ type: 'ack', revision: 2, payload: {} });
  assert.equal(notifications, 1);
});

test('subscriptions coalesce remounts and restore after a fresh reconnect snapshot', async () => {
  const store = setup(), calls = [];
  store.connection.request = async (type, payload) => { calls.push({ type, payload }); return {}; };
  store.connection.status('connected');
  const snapshot = { type: 'graph.snapshot', revision: 1, payload: store.snapshot };
  store.receive(snapshot);
  let off = store.watchArray('amp', 'data', () => {});
  await Promise.resolve();
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0].payload.elements, [{ nodeId: 'amp', element: 'data' }]);
  off(); off = store.watchArray('amp', 'data', () => {});
  await Promise.resolve();
  assert.equal(calls.length, 1);
  store.connection.status('offline');
  store.connection.status('connected');
  store.syncSubscriptions();
  await Promise.resolve();
  assert.equal(calls.length, 1, 'wait for the fresh snapshot before resubscribing');
  store.receive(snapshot);
  await Promise.resolve();
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[1].payload.elements, [{ nodeId: 'amp', element: 'data' }]);
  off();
});

test('an old subscription failure cannot invalidate a new connection subscription', async () => {
  const store = setup(), requests = [];
  store.connection.request = () => new Promise((resolve, reject) => requests.push({ resolve, reject }));
  const snapshot = { type: 'graph.snapshot', revision: 1, payload: store.snapshot };
  store.connection.status('connected');
  store.receive(snapshot);
  const off = store.watchArray('amp', 'data', () => {});
  await Promise.resolve();
  store.connection.status('offline');
  store.connection.status('connected');
  store.receive(snapshot);
  await Promise.resolve();
  assert.equal(requests.length, 2);
  requests[0].reject(Error('Old connection closed'));
  requests[1].resolve();
  await Promise.resolve();
  store.syncSubscriptions();
  await Promise.resolve();
  assert.equal(requests.length, 2);
  assert.equal(store.status.error, '');
  off();
  store.connection.status('offline');
});

test('subscription failures permit retry while successful empty acknowledgements deduplicate', async () => {
  const store = setup();
  let calls = 0;
  store.connection.request = async () => {
    if (++calls === 1) throw Error('Subscription rejected');
  };
  store.connection.status('connected');
  store.receive({ type: 'graph.snapshot', revision: 1, payload: store.snapshot });
  const off = store.watchArray('amp', 'data', () => {});
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(store.status.error, 'Subscription rejected');
  store.syncSubscriptions();
  await Promise.resolve();
  await Promise.resolve();
  store.syncSubscriptions();
  await Promise.resolve();
  assert.equal(calls, 2);
  off();
  store.connection.status('offline');
});
