import test from 'node:test';
import assert from 'node:assert/strict';
import { BackendConnection } from './connection.ts';
import { encodeMessage } from './protocol.ts';

function setup(t) {
  const previousSocket = globalThis.WebSocket, previousWindow = globalThis.window;
  class Socket {
    static OPEN = 1;
    static instances = [];
    readyState = 0;
    constructor() { Socket.instances.push(this); }
    send() {}
    open() { this.readyState = 1; this.onopen?.({}); }
    close(code = 1000, reason = '') { this.readyState = 3; this.onclose?.({ code, reason }); }
    message(message) { this.onmessage?.({ data: encodeMessage(message) }); }
  }
  globalThis.WebSocket = Socket;
  globalThis.window = { location: { hostname: 'localhost' } };
  const states = [], messages = [];
  const connection = new BackendConnection(message => messages.push(message), (state, detail) => states.push({ state, detail }));
  t.after(() => { connection.stop(); globalThis.WebSocket = previousSocket; globalThis.window = previousWindow; });
  return { connection, sockets: Socket.instances, states, messages };
}

test('obsolete sockets cannot publish data or change connection status after remount', t => {
  const { connection, sockets, states, messages } = setup(t);
  connection.start();
  const obsolete = sockets[0];
  connection.stop();
  connection.start();
  obsolete.open();
  obsolete.message({ type: 'graph.snapshot', payload: { stale: true } });
  assert.equal(states.at(-1).state, 'connecting');
  assert.equal(messages.length, 0);
  sockets[1].open();
  obsolete.close(1006, 'late close');
  assert.equal(states.at(-1).state, 'connected');
});

test('disconnect reports its cause and creates only one replacement socket', t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { connection, sockets, states } = setup(t);
  connection.start(); sockets[0].open();
  sockets[0].close(1013, 'Client is too slow');
  assert.equal(states.at(-1).state, 'offline');
  assert.match(states.at(-1).detail, /1013.*Client is too slow/);
  t.mock.timers.tick(1500);
  assert.equal(sockets.length, 2);
  sockets[1].open();
  t.mock.timers.tick(10000);
  assert.equal(sockets.length, 2);
});

test('an obsolete socket cannot acknowledge a new connection request', async t => {
  const { connection, sockets } = setup(t);
  connection.start(); sockets[0].open();
  connection.stop(); connection.start(); sockets[1].open();
  let resolved = false;
  const request = connection.request('graph.get').then(value => { resolved = true; return value; });
  sockets[0].message({ type: 'ack', requestId: 1, payload: { result: 'stale' } });
  await Promise.resolve();
  assert.equal(resolved, false);
  sockets[1].message({ type: 'ack', requestId: 1, payload: { result: 'current' } });
  assert.equal(await request, 'current');
});

test('stopping cancels a queued reconnect', t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { connection, sockets } = setup(t);
  connection.start(); sockets[0].open(); sockets[0].close(1006);
  connection.stop();
  t.mock.timers.tick(10000);
  assert.equal(sockets.length, 1);
  connection.start();
  t.mock.timers.tick(10000);
  assert.equal(sockets.length, 2);
});

test('stopping rejects pending requests and clears their timeout', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const { connection, sockets } = setup(t);
  connection.start(); sockets[0].open();
  const request = connection.request('graph.get');
  connection.stop();
  await assert.rejects(request, /disconnected/);
  t.mock.timers.tick(30000);
  assert.equal(sockets.length, 1);
});
