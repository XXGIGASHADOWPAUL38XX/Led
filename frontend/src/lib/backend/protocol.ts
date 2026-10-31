import { decode, encode } from "@msgpack/msgpack";

export type NumericArray = Float32Array | Float64Array | Int8Array | Uint8Array | Int16Array | Uint16Array | Int32Array | Uint32Array | BigInt64Array | BigUint64Array;
export type ArrayValue = { dtype: string; shape: number[]; data: NumericArray };
export type Message = { type: string; requestId?: number | null; revision?: number; payload: Record<string, unknown> };
export type Endpoint = { nodeId: string; element: string };
export type GraphNode = { id: string; type: string; position: [number, number]; parameters: Record<string, unknown> };
export type Connection = { id: string; source: Endpoint; target: Endpoint };
export type Graph = { nodes: GraphNode[]; connections: Connection[] };
export type ElementDescriptor = {
  name: string; label: string; kind: string; value: unknown; disabled: boolean;
  min?: number; max?: number; integer?: boolean;
  optional?: boolean;
  dtype?: string; defaultType?: string; selectionElements?: string[];
  shape?: number[]; options?: { value: unknown; label: string }[];
  itemPorts?: (string | null)[];
};
export type NodeDescriptor = { id: string; type: string; elements: ElementDescriptor[]; ports: { name: string; direction: "in" | "out"; shape: number[]; accepts?: number[]; adaptiveShape?: boolean; variadic?: boolean }[] };
export type Snapshot = { graph: Graph; nodes: NodeDescriptor[]; catalog: { type: string; description: string }[] };
export type GenerationPreview = { graph: Graph; nodes: Pick<NodeDescriptor, "id" | "type" | "ports">[] };
export type PlayerState = { nodeId: string; tracks: { id: string; title: string; artist: string; duration: number; loaded: boolean }[]; activeTrackId: string | null; playing: boolean; position: number; duration: number };

const arrays = {
  "|b1": Uint8Array, "|u1": Uint8Array, "|i1": Int8Array,
  "<i2": Int16Array, "<u2": Uint16Array, "<i4": Int32Array, "<u4": Uint32Array,
  "<i8": BigInt64Array, "<u8": BigUint64Array, "<f4": Float32Array, "<f8": Float64Array,
};

function restore(value: unknown): unknown {
  if (value instanceof Uint8Array || value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(restore);
  const object = value as Record<string, unknown>;
  if (object.__ndarray__ === true) {
    const Constructor = arrays[object.dtype as keyof typeof arrays];
    const bytes = object.data;
    const shape = object.shape as number[];
    if (!Constructor || !(bytes instanceof Uint8Array) || !Array.isArray(shape) || shape.some((size) => !Number.isSafeInteger(size) || size < 0)) throw Error("Invalid array descriptor");
    const size = shape.reduce((count, dimension) => count * dimension, 1);
    if (!Number.isSafeInteger(size) || size * Constructor.BYTES_PER_ELEMENT !== bytes.byteLength) throw Error("Array shape and byte length disagree");
    // MessagePack bin payloads needn't be aligned for JS typed-array views.
    return { dtype: object.dtype as string, shape, data: new Constructor(bytes.slice().buffer) } satisfies ArrayValue;
  }
  return Object.fromEntries(Object.entries(object).map(([key, item]) => [key, restore(item)]));
}

function prepare(value: unknown): unknown {
  if (isArrayValue(value)) return { __ndarray__: true, dtype: value.dtype, shape: value.shape,
    data: new Uint8Array(value.data.buffer, value.data.byteOffset, value.data.byteLength) };
  if (Array.isArray(value)) return value.map(prepare);
  if (value !== null && typeof value === "object" && !ArrayBuffer.isView(value)) return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, prepare(item)]));
  return value;
}

export function isArrayValue(value: unknown): value is ArrayValue {
  return value !== null && typeof value === "object" && "dtype" in value && "shape" in value && "data" in value && ArrayBuffer.isView(value.data);
}
export function encodeMessage(message: Message) { return encode(prepare(message)); }
export function decodeMessage(data: ArrayBuffer | Uint8Array): Message {
  const message = restore(decode(new Uint8Array(data))) as Message;
  if (!message || typeof message.type !== "string" || !message.payload || typeof message.payload !== "object" || Array.isArray(message.payload)) throw Error("Invalid message envelope");
  return message;
}
