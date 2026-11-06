import assert from "node:assert/strict";
import test from "node:test";
import { completeConfiguration, compatiblePorts } from "./configuration.ts";

// OperatorPipeline.arguments and GroupNode.nodes, as their Python classes declare them.
const expression = { name: "arguments", control: "expression", addPort: "add_element", item: "token" };
const sequence = { name: "nodes", control: "sequence", item: "node" };

test("unfinished references cannot be applied; literals and completed references can", () => {
  const fields = [expression];
  assert.equal(completeConfiguration(fields, { arguments: [null, "*", 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{}, "*", 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{ nodeId: "a" }, "*", 1] }), false);
  assert.equal(completeConfiguration(fields, { arguments: [{ nodeId: "a", element: "data" }, "*", 1] }), true);
  assert.equal(completeConfiguration([sequence], { nodes: [{ nodeId: "a" }] }), true);
});

test("connection choices exclude incompatible array ranks and fixed dimensions", () => {
  assert.equal(compatiblePorts({ shape: [2, 2048] }, { shape: [2, 2048] }), true);
  assert.equal(compatiblePorts({ shape: [180] }, { shape: [0] }), true);
  assert.equal(compatiblePorts({ shape: [2, 100] }, { shape: [2, 335] }), false);
  assert.equal(compatiblePorts({ shape: [180, 4] }, { shape: [180] }), false);
  assert.equal(compatiblePorts({ shape: [335] }, { shape: [2, 2048], adaptiveShape: true }), true);
  assert.equal(compatiblePorts({ shape: [4, 335] }, { shape: [2, 2048], adaptiveShape: true }), true);
  assert.equal(compatiblePorts({ shape: [] }, { shape: [2, 2048], adaptiveShape: true }), false);
  assert.equal(compatiblePorts({ shape: [2, 0] }, { shape: [2, 2048], adaptiveShape: true }), false);
});

test("explicit accepts constrain variadic scalar and adaptive RGB ports", () => {
  assert.equal(compatiblePorts({ shape: [1] }, { shape: [], variadic: true, accepts: [1] }), true);
  assert.equal(compatiblePorts({ shape: [180] }, { shape: [], variadic: true, accepts: [1] }), false);
  assert.equal(compatiblePorts({ shape: [178] }, { shape: [180], adaptiveShape: true, accepts: [0] }), true);
  assert.equal(compatiblePorts({ shape: [178, 3] }, { shape: [180], adaptiveShape: true, accepts: [0] }), false);
  assert.equal(compatiblePorts({ shape: [178, 3] }, { shape: [180, 3], adaptiveShape: true, accepts: [0, 3] }), true);
  assert.equal(compatiblePorts({ shape: [178, 4] }, { shape: [180, 3], adaptiveShape: true, accepts: [0, 3] }), false);
});
