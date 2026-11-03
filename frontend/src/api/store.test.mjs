import test from "node:test";
import assert from "node:assert/strict";
import { BackendStore } from "./store.ts";

const descriptor = (value) => ({
  id: "amp",
  type: "Amplitudes",
  elements: [{ name: "powering", value }],
  ports: [{ name: "data", direction: "out" }],
});
function setup() {
  const store = new BackendStore();
  store.connection.send = () => {};
  store.receive({
    type: "graph.snapshot",
    revision: 1,
    payload: { graph: { nodes: [], connections: [] }, nodes: [descriptor(0.5)] },
  });
  return store;
}

test("frames notify only the subscribed array, not graph or controls", () => {
  const store = setup();
  let graphs = 0,
    controls = 0,
    arrays = 0;
  store.subscribe("graph", () => graphs++);
  store.subscribe("node:amp", () => controls++);
  store.watchArray("amp", "data", () => arrays++);
  store.receive({
    type: "frame",
    revision: 1,
    payload: {
      sequence: 1,
      values: [{ nodeId: "amp", element: "data", value: { dtype: "<f4", shape: [1], data: new Float32Array([1]) } }],
      players: [],
    },
  });
  assert.equal(graphs, 0);
  assert.equal(controls, 0);
  assert.equal(arrays, 1);
});

test("an older edit response cannot overwrite a newer optimistic value", async () => {
  const store = setup();
  const resolve = [];
  store.connection.request = () => new Promise((done) => resolve.push(done));
  const first = store.setElement("amp", "powering", 0.75);
  const second = store.setElement("amp", "powering", 1);
  store.receive({ type: "state.update", revision: 2, payload: { node: descriptor(0.75) } });
  resolve[0]({ value: 0.75 });
  await first;
  assert.equal(store.node("amp").elements[0].value, 1);
  store.receive({ type: "state.update", revision: 3, payload: { node: descriptor(1) } });
  resolve[1]({ value: 1 });
  await second;
  assert.equal(store.node("amp").elements[0].value, 1);
});

test("rejected edits restore authoritative state and expose the error", async () => {
  const store = setup();
  store.connection.request = async () => {
    throw Error("Out of range");
  };
  await store.setElement("amp", "powering", 100);
  assert.equal(store.node("amp").elements[0].value, 0.5);
  assert.equal(store.status.error, "Out of range");
});

test("batched positions update the graph once and preserve streamed data", () => {
  const store = setup();
  store.snapshot.graph.nodes = ["amp", "buffer"].map((id) => ({ id, position: [0, 0] }));
  const value = { dtype: "<f4", shape: [1], data: new Float32Array([1]) };
  store.receive({
    type: "frame",
    revision: 1,
    payload: { sequence: 1, values: [{ nodeId: "amp", element: "data", value }], players: [] },
  });
  let updates = 0;
  store.subscribe("graph", () => updates++);
  store.receive({ type: "state.update", revision: 2, payload: { positions: { amp: [400, 24], buffer: [24, 24] } } });
  assert.equal(updates, 1);
  assert.deepEqual(
    store.snapshot.graph.nodes.map((node) => node.position),
    [
      [400, 24],
      [24, 24],
    ],
  );
  assert.equal(store.array("amp", "data"), value);
});

test("acks at the current revision do not notify status listeners", () => {
  const store = setup();
  let updates = 0;
  store.subscribe("status", () => updates++);
  store.receive({ type: "ack", revision: 1, requestId: 7, payload: { command: "subscribe" } });
  assert.equal(updates, 0);
  store.receive({ type: "ack", revision: 2, requestId: 8, payload: { command: "element.set" } });
  assert.equal(updates, 1);
  assert.equal(store.status.revision, 2);
});

const generation = (status, mode = "generate") => ({
  type: "jev.update",
  revision: 1,
  payload: { status, message: "", nodes: 0, mode },
});

test("a completed generation replaces the canvas and its view settings; an edit keeps them", () => {
  const store = setup();
  store.setViewSettings("amp", "bars", { open: true });
  store.receive(generation("running"));
  store.receive({ type: "jev.preview", revision: 1, payload: { graph: { nodes: [], connections: [] }, nodes: [] } });
  assert.notEqual(store.generationPreview, null);
  store.receive(generation("complete"));
  assert.equal(store.viewSettings("amp", "bars").open, undefined);
  assert.equal(store.generationPreview, null);
  assert.equal(store.generation.status, "complete");

  store.setViewSettings("amp", "bars", { open: true });
  store.receive(generation("running", "edit"));
  store.receive(generation("complete", "edit"));
  assert.equal(store.viewSettings("amp", "bars").open, true);
});

test("a generation still running keeps its preview; one that never ran keeps the view settings", () => {
  const store = setup();
  store.setViewSettings("amp", "bars", { open: true });
  store.receive(generation("running"));
  store.receive({ type: "jev.preview", revision: 1, payload: { graph: { nodes: [], connections: [] }, nodes: [] } });
  store.receive(generation("running"));
  assert.notEqual(store.generationPreview, null);
  store.receive(generation("cancelled"));
  store.receive(generation("complete"));
  assert.equal(store.viewSettings("amp", "bars").open, true);
});

test("every full snapshot starts a new graph epoch, in the same step that installs the graph", () => {
  const store = setup();
  assert.equal(store.graphEpoch, 1);
  let seen = null;
  store.subscribe("epoch", () => (seen = store.snapshot.graph.nodes.map((node) => node.id)));
  store.receive({
    type: "graph.snapshot",
    revision: 2,
    payload: {
      graph: { nodes: [{ id: "fresh", type: "Buffer", position: [0, 0], parameters: {} }], connections: [] },
      nodes: [],
    },
  });
  assert.equal(store.graphEpoch, 2);
  assert.deepEqual(seen, ["fresh"]);
  store.receive(patch(2, { nodeOrder: ["fresh"] }));
  assert.equal(store.graphEpoch, 2);
});

test("frames from an older revision are dropped but still acknowledged", () => {
  const store = setup();
  const sent = [];
  store.connection.send = (type, payload) => sent.push([type, payload]);
  const value = { dtype: "<f4", shape: [1], data: new Float32Array([1]) };
  store.receive({
    type: "frame",
    revision: 0,
    payload: { sequence: 4, values: [{ nodeId: "amp", element: "data", value }], players: [{ nodeId: "p" }] },
  });
  assert.equal(store.array("amp", "data"), null);
  assert.equal(store.player("p"), null);
  assert.deepEqual(sent, [["frame.ack", { sequence: 4 }]]);
  store.receive({
    type: "frame",
    revision: 1,
    payload: { sequence: 5, values: [{ nodeId: "amp", element: "data", value }], players: [{ nodeId: "p" }] },
  });
  assert.equal(store.array("amp", "data"), value);
  assert.deepEqual(store.player("p"), { nodeId: "p" });
});

test("streams subscribe once connected with a snapshot, and only to ports that exist", async () => {
  const store = new BackendStore();
  const requests = [];
  store.connection.request = async (type, payload) => requests.push([type, payload.elements]);
  store.status = { ...store.status, connection: "connected" };
  store.watchArray("amp", "data", () => {});
  assert.deepEqual(requests, []);
  store.receive({
    type: "graph.snapshot",
    revision: 1,
    payload: { graph: { nodes: [], connections: [] }, nodes: [descriptor(0.5)] },
  });
  store.watchArray("amp", "missing", () => {});
  assert.deepEqual(requests, [
    ["subscribe", [{ nodeId: "amp", element: "data" }]],
    ["subscribe", [{ nodeId: "amp", element: "data" }]],
  ]);
});

test("a node update notifies that node only, not the graph", () => {
  const store = setup();
  let graphs = 0;
  store.subscribe("graph", () => graphs++);
  store.receive({ type: "state.update", revision: 2, payload: { node: descriptor(0.25) } });
  assert.equal(graphs, 0);
  assert.equal(store.node("amp").elements[0].value, 0.25);
});

test("a snapshot during an edit wins over the optimistic value", async () => {
  const store = setup();
  let resolve;
  store.connection.request = () => new Promise((done) => (resolve = done));
  const edit = store.setElement("amp", "powering", 0.75);
  assert.equal(store.node("amp").elements[0].value, 0.75);
  store.receive({
    type: "graph.snapshot",
    revision: 2,
    payload: { graph: { nodes: [], connections: [] }, nodes: [descriptor(0.3)] },
  });
  resolve({ value: 0.75 });
  await edit;
  assert.equal(store.node("amp").elements[0].value, 0.3);
});

test("unwatched streams and streams of unknown nodes leave the subscription", () => {
  const store = setup();
  const requests = [];
  store.connection.request = async (type, payload) => requests.push(payload.elements);
  store.status = { ...store.status, connection: "connected" };
  const first = store.watchArray("amp", "data", () => {});
  const second = store.watchArray("amp", "data", () => {});
  store.watchArray("gone", "data", () => {});
  first();
  assert.deepEqual(requests.at(-1), [{ nodeId: "amp", element: "data" }]);
  second();
  assert.deepEqual(requests.at(-1), []);
});

const patch = (base, changes) => ({
  type: "graph.patch",
  revision: base + 1,
  payload: { base, nodeOrder: ["amp"], connectionOrder: [], nodes: [], connections: [], descriptors: [], ...changes },
});

test("a graph patch updates only the changed nodes and keeps the others' streams", () => {
  const store = new BackendStore();
  store.connection.send = () => {};
  store.connection.request = async () => {};
  const node = (id) => ({ id, type: "Buffer", position: [0, 0], parameters: {} });
  store.receive({
    type: "graph.snapshot",
    revision: 1,
    payload: {
      graph: { nodes: [node("amp"), node("gone")], connections: [] },
      nodes: [descriptor(0.5), { ...descriptor(0), id: "gone" }],
    },
  });
  const value = { dtype: "<f4", shape: [1], data: new Float32Array([1]) };
  store.receive({
    type: "frame",
    revision: 1,
    payload: {
      sequence: 1,
      values: [
        { nodeId: "amp", element: "data", value },
        { nodeId: "gone", element: "data", value },
      ],
      players: [],
    },
  });
  store.setViewSettings("gone", "bars", { open: true });
  let amp = 0;
  store.subscribe("node:amp", () => amp++);
  store.receive(
    patch(1, {
      nodeOrder: ["amp", "new"],
      nodes: [node("new")],
      descriptors: [{ ...descriptor(0), id: "new" }],
    }),
  );
  assert.deepEqual(
    store.snapshot.graph.nodes.map((item) => item.id),
    ["amp", "new"],
  );
  assert.equal(amp, 0);
  assert.equal(store.array("amp", "data"), value);
  assert.equal(store.array("gone", "data"), null);
  assert.equal(store.node("gone"), null);
  assert.equal(store.node("new").id, "new");
  assert.equal(store.viewSettings("gone", "bars").open, undefined);
  assert.equal(store.status.revision, 2);
});

test("a patch from another revision triggers a full resync instead of a wrong merge", async () => {
  const store = setup();
  let resyncs = 0;
  store.resync = async () => resyncs++;
  store.receive(patch(5, { nodeOrder: [] }));
  assert.equal(resyncs, 1);
  assert.equal(store.node("amp").id, "amp");
});

test("an HTTP command resolves once this tab has received the revision it produced", async () => {
  const store = new BackendStore("http://backend", async () =>
    Response.json({ nodeIds: ["copy"] }, { headers: { "X-Revision": "2" } }),
  );
  store.connection.send = () => {};
  store.connection.request = async () => {};
  store.status = { ...store.status, connection: "connected" };
  store.receive({
    type: "graph.snapshot",
    revision: 1,
    payload: { graph: { nodes: [], connections: [] }, nodes: [] },
  });
  let done = false;
  const pasted = store.graph.paste({ nodes: [], connections: [] }, [0, 0]).then((result) => {
    done = true;
    return result;
  });
  await new Promise((resolve) => setTimeout(resolve, 10));
  assert.equal(done, false);
  store.receive(
    patch(1, {
      nodeOrder: ["copy"],
      nodes: [{ id: "copy", type: "Buffer", position: [0, 0], parameters: {} }],
      descriptors: [{ ...descriptor(0), id: "copy" }],
    }),
  );
  assert.deepEqual(await pasted, { nodeIds: ["copy"] });
  assert.equal(store.node("copy").id, "copy");
});

test("a command does not wait for a revision once the connection is lost", async () => {
  const store = new BackendStore("http://backend", async () =>
    Response.json({ revision: 9 }, { headers: { "X-Revision": "9" } }),
  );
  store.status = { ...store.status, connection: "connected" };
  const removed = store.graph.removeNode("amp");
  await new Promise((resolve) => setTimeout(resolve, 10));
  store.status = { ...store.status, connection: "offline" };
  store.receive({ type: "error", payload: { message: "Backend disconnected" } });
  assert.deepEqual(await removed, { revision: 9 });
});
