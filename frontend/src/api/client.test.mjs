import test from "node:test";
import assert from "node:assert/strict";
import { refusal } from "./client.ts";

test("refusals read our text details, FastAPI's validation lists, and nothing else", () => {
  assert.equal(refusal({ detail: "Unknown connection" }), "Unknown connection");
  assert.equal(
    refusal({ detail: [{ msg: "Field required" }, { msg: "Input should be a valid number" }] }),
    "Field required; Input should be a valid number",
  );
  for (const body of [null, "Internal Server Error", { detail: 42 }, {}]) assert.equal(refusal(body), "Request failed");
});
