import test from "node:test";
import assert from "node:assert/strict";
import { encode } from "@msgpack/msgpack";
import { decodeMessage, encodeMessage, fromJson, toJson } from "./protocol.ts";

test("controls and arrays use the same MessagePack envelope", () => {
  const control = {
    type: "ack",
    requestId: 9,
    revision: 2,
    payload: { nodeId: "amp", element: "powering", value: 0.75 },
  };
  assert.deepEqual(decodeMessage(encodeMessage(control)), control);
  const array = { dtype: "<f4", shape: [2, 2], data: new Float32Array([1, 2, 3, 4]) };
  const result = decodeMessage(encodeMessage({ type: "frame", revision: 4, payload: { array } }));
  assert.deepEqual(result.payload.array.shape, [2, 2]);
  assert.deepEqual([...result.payload.array.data], [1, 2, 3, 4]);
  assert(result.payload.array.data instanceof Float32Array);
});

test("decodes unaligned binary, scalar, empty and int64 arrays", () => {
  for (const array of [
    { dtype: "<f8", shape: [], data: new Float64Array([1.5]) },
    { dtype: "<i8", shape: [2], data: new BigInt64Array([1n, 9007199254740993n]) },
    { dtype: "<f4", shape: [0, 2], data: new Float32Array(0) },
  ]) {
    const result = decodeMessage(
      encodeMessage({ type: "frame", revision: 1, payload: { longKeyCausesDifferentAlignment: array } }),
    );
    assert.deepEqual(result.payload.longKeyCausesDifferentAlignment.shape, array.shape);
    assert.deepEqual([...result.payload.longKeyCausesDifferentAlignment.data], [...array.data]);
  }
});

test("rejects malformed array descriptors", () => {
  for (const descriptor of [
    { dtype: "|O", shape: [1], data: new Uint8Array(8) },
    { dtype: "<f4", shape: [-1], data: new Uint8Array(0) },
    { dtype: "<f4", shape: [100], data: new Uint8Array(4) },
  ])
    assert.throws(() =>
      decodeMessage(encode({ type: "frame", revision: 1, payload: { array: { __ndarray__: true, ...descriptor } } })),
    );
});

test("arrays cross JSON as base64 envelopes, readable by the backend's from_json", () => {
  const curve = { dtype: "<f8", shape: [2], data: new Float64Array([0.5, -1.25]) };
  const json = toJson({ graph: { nodes: [{ parameters: { curve, level: 0.5 } }] } });
  const envelope = json.graph.nodes[0].parameters.curve;
  assert.deepEqual(envelope, {
    __ndarray__: true,
    dtype: "<f8",
    shape: [2],
    data: Buffer.from(curve.data.buffer).toString("base64"),
  });
  const back = fromJson(JSON.parse(JSON.stringify(json)));
  assert.deepEqual([...back.graph.nodes[0].parameters.curve.data], [0.5, -1.25]);
  assert(back.graph.nodes[0].parameters.curve.data instanceof Float64Array);
  assert.equal(back.graph.nodes[0].parameters.level, 0.5);
  assert.throws(() => fromJson({ __ndarray__: true, dtype: "<f8", shape: [3], data: "AAAA" }), /disagree/);
});

test("server messages must name their revision", () => {
  assert.throws(() => decodeMessage(encode({ type: "ack", payload: {} })), /Invalid message envelope/);
  assert.equal(decodeMessage(encode({ type: "ack", revision: 3, payload: {} })).revision, 3);
});
