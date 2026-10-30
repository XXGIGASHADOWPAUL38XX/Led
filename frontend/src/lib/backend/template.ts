import { decodeMessage, encodeMessage, type Graph } from "./protocol.ts";

export type DisplayColor = [number, number, number] | [number, number, number, number];
export type ViewSettings = {
  open?: boolean; title?: string; range?: [number, number] | null;
  historyLength?: number; lineColors?: Record<string, DisplayColor>;
  hiddenSeries?: string[]; expanded?: boolean;
};
export type DisplayState = Record<string, Record<string, ViewSettings>>;
export type Template = { version: 1; graph: Graph; ui: DisplayState };
export const MAX_TEMPLATE_BYTES = 64 * 1024 * 1024;
export const emptyViewSettings: ViewSettings = Object.freeze({});
export const viewKey = (kind: string, data = "") => JSON.stringify([kind, data]);

const object = (value: unknown): value is Record<string, unknown> => value !== null && typeof value === "object" && !Array.isArray(value);
const nonempty = (value: unknown): value is string => typeof value === "string" && value.length > 0;
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
function endpoint(value: unknown) {
  return object(value) && nonempty(value.nodeId) && nonempty(value.element);
}
function validSettings(value: unknown) {
  if (!object(value)) return false;
  const allowed = new Set(["open", "title", "range", "historyLength", "lineColors", "hiddenSeries", "expanded"]);
  if (Object.keys(value).some((key) => !allowed.has(key))) return false;
  if (value.open !== undefined && typeof value.open !== "boolean" || value.expanded !== undefined && typeof value.expanded !== "boolean") return false;
  if (value.title !== undefined && typeof value.title !== "string") return false;
  if (value.range !== undefined && value.range !== null && !(Array.isArray(value.range) && value.range.length === 2 && value.range.every(finite) && value.range[0] < value.range[1])) return false;
  if (value.historyLength !== undefined && !(finite(value.historyLength) && Number.isInteger(value.historyLength) && value.historyLength >= 10 && value.historyLength <= 1000)) return false;
  if (value.hiddenSeries !== undefined && !(Array.isArray(value.hiddenSeries) && value.hiddenSeries.every((id) => typeof id === "string"))) return false;
  if (value.lineColors !== undefined && !(object(value.lineColors) && Object.values(value.lineColors).every((color) => Array.isArray(color) && [3, 4].includes(color.length) && color.every((channel) => finite(channel) && channel >= 0 && channel <= 255)))) return false;
  return true;
}

function validate(value: unknown): asserts value is Template {
  if (!object(value) || value.version !== 1) throw Error("Unsupported template version. Expected version 1.");
  const graph = value.graph;
  if (!object(graph) || !Array.isArray(graph.nodes) || !Array.isArray(graph.connections)) throw Error("Invalid template graph.");
  const ids = new Set<string>();
  for (const node of graph.nodes) {
    if (!object(node) || !nonempty(node.id) || !nonempty(node.type) || !object(node.parameters) || !Array.isArray(node.position) || node.position.length !== 2 || !node.position.every(finite) || ids.has(node.id)) throw Error("Invalid template node.");
    ids.add(node.id);
  }
  if (graph.connections.some((edge) => !object(edge) || !nonempty(edge.id) || !endpoint(edge.source) || !endpoint(edge.target))) throw Error("Invalid template connection.");
  if (!object(value.ui) || Object.entries(value.ui).some(([id, views]) => !ids.has(id) || !object(views) || Object.values(views).some((settings) => !validSettings(settings)))) throw Error("Invalid template display settings.");
}

export function encodeTemplate(template: Template) {
  validate(template);
  const bytes = encodeMessage({ type: "template", payload: template });
  if (bytes.byteLength > MAX_TEMPLATE_BYTES) throw Error("Template exceeds 64 MB.");
  return bytes;
}
export function decodeTemplate(bytes: ArrayBuffer | Uint8Array): Template {
  if (bytes.byteLength > MAX_TEMPLATE_BYTES) throw Error("Template exceeds 64 MB.");
  const message = decodeMessage(bytes);
  if (message.type !== "template") throw Error("Choose a .led template file.");
  validate(message.payload);
  return message.payload;
}
