import { decode, encode } from "@msgpack/msgpack";
import type { components } from "./schema";

export type NumericArray =
  | Float32Array
  | Float64Array
  | Int8Array
  | Uint8Array
  | Int16Array
  | Uint16Array
  | Int32Array
  | Uint32Array
  | BigInt64Array
  | BigUint64Array;
export type ArrayValue = { dtype: string; shape: number[]; data: NumericArray };
/** The WebSocket envelope; every server message carries the revision it was sent at. */
export type Message = { type: string; requestId?: number | null; revision: number; payload: Record<string, unknown> };
/** What the client encodes: commands and template files name no revision. */
export type Outgoing = Omit<Message, "revision">;
// Wire types are generated from the Python contract (backend/api/schemas.py): npm run api:generate.
type Schemas = components["schemas"];
export type Endpoint = Schemas["Endpoint"];
export type GraphNode = Schemas["GraphNode-Output"];
export type Connection = Schemas["Connection"];
export type Graph = Schemas["Graph-Output"];
export type ElementDescriptor = Schemas["ElementDescriptor"];
export type NodeDescriptor = Schemas["NodeDescriptor"];
export type Snapshot = Schemas["Snapshot"];
export type GenerationPreview = Schemas["GenerationPreview"];
export type GenerationState = Schemas["GenerationState"];
export type PlayerState = Schemas["PlayerState"];
export type GraphPatch = Schemas["GraphPatch"];
export type GraphState = Schemas["GraphState"];

const arrays = {
  "|b1": Uint8Array,
  "|u1": Uint8Array,
  "|i1": Int8Array,
  "<i2": Int16Array,
  "<u2": Uint16Array,
  "<i4": Int32Array,
  "<u4": Uint32Array,
  "<i8": BigInt64Array,
  "<u8": BigUint64Array,
  "<f4": Float32Array,
  "<f8": Float64Array,
};

function restoreArray(object: Record<string, unknown>): ArrayValue {
  const Constructor = arrays[object.dtype as keyof typeof arrays];
  const bytes = object.data;
  const shape = object.shape as number[];
  if (
    !Constructor ||
    !(bytes instanceof Uint8Array) ||
    !Array.isArray(shape) ||
    shape.some((size) => !Number.isSafeInteger(size) || size < 0)
  )
    throw Error("Invalid array descriptor");
  const size = shape.reduce((count, dimension) => count * dimension, 1);
  if (!Number.isSafeInteger(size) || size * Constructor.BYTES_PER_ELEMENT !== bytes.byteLength)
    throw Error("Array shape and byte length disagree");
  // MessagePack bin payloads needn't be aligned for JS typed-array views.
  return { dtype: object.dtype as string, shape, data: new Constructor(bytes.slice().buffer) };
}

function restore(value: unknown): unknown {
  if (value instanceof Uint8Array || value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(restore);
  const object = value as Record<string, unknown>;
  if (object.__ndarray__ === true) return restoreArray(object);
  return Object.fromEntries(Object.entries(object).map(([key, item]) => [key, restore(item)]));
}

function prepare(value: unknown): unknown {
  if (isArrayValue(value))
    return {
      __ndarray__: true,
      dtype: value.dtype,
      shape: value.shape,
      data: new Uint8Array(value.data.buffer, value.data.byteOffset, value.data.byteLength),
    };
  if (Array.isArray(value)) return value.map(prepare);
  if (value !== null && typeof value === "object" && !ArrayBuffer.isView(value))
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, prepare(item)]));
  return value;
}

export function isArrayValue(value: unknown): value is ArrayValue {
  return (
    value !== null &&
    typeof value === "object" &&
    "dtype" in value &&
    "shape" in value &&
    "data" in value &&
    ArrayBuffer.isView(value.data)
  );
}
/** Apply `data` to the payload of every array envelope, leaving everything else as is. */
function mapEnvelopes(value: unknown, data: (bytes: unknown) => unknown): unknown {
  if (Array.isArray(value)) return value.map((item) => mapEnvelopes(item, data));
  if (value === null || typeof value !== "object" || ArrayBuffer.isView(value)) return value;
  const object = value as Record<string, unknown>;
  if (object.__ndarray__ === true) return { ...object, data: data(object.data) };
  return Object.fromEntries(Object.entries(object).map(([key, item]) => [key, mapEnvelopes(item, data)]));
}
const toBase64 = (bytes: unknown) => {
  let binary = "";
  const view = bytes as Uint8Array;
  for (let start = 0; start < view.length; start += 0x8000)
    binary += String.fromCharCode(...view.subarray(start, start + 0x8000));
  return btoa(binary);
};
const fromBase64 = (text: unknown) => Uint8Array.from(atob(String(text)), (char) => char.charCodeAt(0));

/** JSON-ready copy for the HTTP API: arrays use the MessagePack envelope with base64 data. */
export function toJson(value: unknown): unknown {
  return mapEnvelopes(prepare(value), toBase64);
}
/** Inverse of toJson; array envelopes are checked as in MessagePack. */
export function fromJson(value: unknown): unknown {
  return restore(mapEnvelopes(value, fromBase64));
}
export function encodeMessage(message: Outgoing) {
  return encode(prepare(message));
}
/** A MessagePack envelope with a type and an object payload: server messages and saved template files. */
export function decodeEnvelope(data: ArrayBuffer | Uint8Array): Outgoing {
  const message = restore(decode(new Uint8Array(data))) as Outgoing;
  if (
    !message ||
    typeof message.type !== "string" ||
    !message.payload ||
    typeof message.payload !== "object" ||
    Array.isArray(message.payload)
  )
    throw Error("Invalid message envelope");
  return message;
}
/** A server message, which also names the revision it was sent at. */
export function decodeMessage(data: ArrayBuffer | Uint8Array): Message {
  const message = decodeEnvelope(data) as Message;
  if (typeof message.revision !== "number") throw Error("Invalid message envelope");
  return message;
}
