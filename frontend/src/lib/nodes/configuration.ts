import type { FieldDefinition } from "../../components/node/definition.ts";
import { isArrayValue } from "../backend/protocol.ts";

export function completeConfiguration(fields: FieldDefinition[], draft: Record<string, unknown>) {
  return fields.every((field) => {
    if (field.control !== "sequence" || !Object.hasOwn(draft, field.name)) return true;
    return (draft[field.name] as unknown[]).every((value) => {
      if (field.item === "token" && (isArrayValue(value) || typeof value === "string" || typeof value === "number" && Number.isFinite(value))) return true;
      if (value === null || typeof value !== "object" || !("nodeId" in value) || typeof value.nodeId !== "string") return false;
      return field.item === "node" || "element" in value && typeof value.element === "string";
    });
  });
}

export function compatiblePorts(source: { shape: number[] }, target: { shape: number[]; accepts?: number[] }) {
  const shape = target.accepts ?? target.shape;
  return source.shape.length === shape.length && shape.every((dimension, index) => dimension === 0 || dimension === source.shape[index]);
}
