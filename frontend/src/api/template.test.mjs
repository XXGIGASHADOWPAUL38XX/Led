import test from "node:test";
import assert from "node:assert/strict";
import { encodeMessage, fromJson, toJson } from "./protocol.ts";
import { encodeTemplate, decodeTemplate, viewKey } from "./template.ts";
import { BackendStore } from "./store.ts";

const graph = () => ({
  nodes: [
    {
      id: "curve",
      type: "Function",
      position: [125, -30],
      parameters: {
        points: { dtype: "<f4", shape: [2, 2], data: new Float32Array([0, 0, 1, 1]) },
      },
    },
  ],
  connections: [],
});
const settings = {
  open: false,
  title: "My spectrum",
  range: [0, 42],
  historyLength: 250,
  lineColors: { 0: [12, 34, 56, 128] },
  hiddenSeries: ["1"],
  expanded: false,
  axisRanges: { 0: [0, 2], 3: [5, -1] },
};
const template = () => ({
  version: 1,
  graph: graph(),
  ui: { curve: { [viewKey("history", "data")]: structuredClone(settings) } },
});
function snapshot(store, value) {
  store.receive({
    type: "graph.snapshot",
    revision: 1,
    payload: {
      graph: value,
      nodes: value.nodes.map((node) => ({ id: node.id, type: node.type, elements: [], ports: [] })),
      catalog: [],
    },
  });
}

test("templates preserve positions, dtype, shape, and all display settings", () => {
  const original = template();
  const restored = decodeTemplate(encodeTemplate(original));
  assert.deepEqual(restored, original);
  assert.ok(restored.graph.nodes[0].parameters.points.data instanceof Float32Array);
  original.graph.nodes[0].parameters.points = {
    dtype: "<i8",
    shape: [1],
    data: new BigInt64Array([9007199254740993n]),
  };
  assert.equal(decodeTemplate(encodeTemplate(original)).graph.nodes[0].parameters.points.data[0], 9007199254740993n);
});

test("bad versions, files, graphs, and display settings are rejected", () => {
  const pack = (value) => encodeMessage({ type: "template", payload: value });
  for (const invalid of [
    { ...template(), version: 2 },
    { ...template(), graph: { nodes: "bad", connections: [] } },
    { ...template(), ui: { curve: { chart: { range: [4, 1] } } } },
    { ...template(), ui: { curve: { chart: { historyLength: 1e9 } } } },
    { ...template(), ui: { curve: { chart: { lineColors: { 0: [999, 0, 0] } } } } },
    { ...template(), ui: { missing: {} } },
  ])
    assert.throws(() => decodeTemplate(pack(invalid)));
  assert.throws(() => decodeTemplate(encodeMessage({ type: "frame", payload: {} })), /template file/);
  assert.throws(() => decodeTemplate(new Uint8Array([0xc1])));
});

/** A store whose HTTP calls reach `respond(method, path, body)` instead of the network. */
function storeWith(respond) {
  return new BackendStore("http://backend", async (request) => {
    const body = request.method === "GET" ? undefined : fromJson(JSON.parse(await request.text()));
    const [status, reply] = await respond(request.method, new URL(request.url).pathname, body);
    return Response.json(toJson(reply), { status });
  });
}

test("saving gets current Python values instead of a stale frontend graph", async () => {
  const fresh = graph();
  fresh.nodes[0].position = [200, 300];
  const store = storeWith(async (method, path) => {
    assert.deepEqual([method, path], ["GET", "/api/v1/graph"]);
    return [200, { graph: fresh, nodes: [], revision: 3 }];
  });
  snapshot(store, { nodes: [], connections: [] });
  const saved = decodeTemplate(await store.exportTemplate());
  assert.deepEqual(saved.graph.nodes[0].position, [200, 300]);
  assert.equal(saved.graph.nodes[0].parameters.points.data.length, 4);
  assert.equal(Object.hasOwn(saved, "players"), false);
});

test("display restoration waits for acceptance and notifies relevant views", async () => {
  let resolve;
  const store = storeWith(async (method, path, body) => {
    assert.deepEqual([method, path], ["PUT", "/api/v1/graph"]);
    assert.deepEqual(body.graph, graph());
    return new Promise((done) => {
      resolve = done;
    });
  });
  const key = viewKey("history", "data");
  snapshot(store, graph());
  store.setViewSettings("curve", key, { title: "Current" });
  let updates = 0,
    frames = 0;
  store.subscribe(`display:${JSON.stringify(["curve", key])}`, () => updates++);
  store.subscribe("array:other", () => frames++);
  const pending = store.importTemplate(encodeTemplate(template()));
  assert.equal(store.viewSettings("curve", key).title, "Current");
  while (!resolve) await new Promise((done) => setTimeout(done));
  resolve([200, { revision: 2 }]);
  await pending;
  assert.deepEqual(store.viewSettings("curve", key), settings);
  assert.equal(updates, 1);
  assert.equal(frames, 0);
});

test("failed imports preserve display state; malformed files never reach Python", async () => {
  let requests = 0;
  const store = storeWith(async () => {
    requests++;
    return [422, { detail: "Unknown node" }];
  });
  const key = viewKey("history", "data");
  snapshot(store, graph());
  store.setViewSettings("curve", key, { title: "Keep me" });
  await assert.rejects(store.importTemplate(encodeTemplate(template())), /Unknown node/);
  assert.equal(store.viewSettings("curve", key).title, "Keep me");
  await assert.rejects(store.importTemplate(new Uint8Array([0xc1])));
  assert.equal(requests, 1);
});

test("view settings survive refreshes and are removed with deleted nodes", () => {
  const store = new BackendStore();
  const key = viewKey("bars", "data");
  snapshot(store, graph());
  store.setViewSettings("curve", key, { open: false });
  snapshot(store, graph());
  assert.equal(store.viewSettings("curve", key).open, false);
  snapshot(store, { nodes: [], connections: [] });
  assert.deepEqual(store.viewSettings("curve", key), {});
});

test("a template's view settings arrive with its graph, before the canvas lays it out", async () => {
  const key = viewKey("history", "data");
  const store = storeWith(async () => {
    store.receive({ type: "graph.snapshot", revision: 5, payload: { graph: graph(), nodes: [] } });
    return [200, { revision: 5 }];
  });
  store.connection.request = async () => {};
  store.status = { ...store.status, connection: "connected" };
  let seen = null;
  store.subscribe("epoch", () => (seen = store.viewSettings("curve", key)));
  await store.importTemplate(encodeTemplate(template()));
  assert.deepEqual(seen, settings);
});

test("axis ranges require numeric indices and two finite, distinct endpoints", () => {
  for (const axisRanges of [
    { x: [0, 1] },
    { "-1": [0, 1] },
    { 1.5: [0, 1] },
    { 0: [0] },
    { 0: [0, 1, 2] },
    { 0: [0, NaN] },
    { 0: [Infinity, 1] },
    { 0: ["0", 1] },
    { 0: [1, 1] },
  ]) {
    const invalid = template();
    invalid.ui.curve[viewKey("history", "data")].axisRanges = axisRanges;
    assert.throws(() => decodeTemplate(encodeMessage({ type: "template", payload: invalid })), /display settings/);
  }
});
