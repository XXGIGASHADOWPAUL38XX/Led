import type { FieldDefinition } from "../../components/node/definition.ts";

export function completeConfiguration(fields: FieldDefinition[], draft: Record<string, unknown>) {
  return fields.every((field) => {
    if (field.control !== "sequence" || !Object.hasOwn(draft, field.name)) return true;
    return (draft[field.name] as unknown[]).every((value) => {
      if (field.item === "token" && (typeof value === "string" || typeof value === "number" && Number.isFinite(value))) return true;
      if (value === null || typeof value !== "object" || !("nodeId" in value) || typeof value.nodeId !== "string") return false;
      return field.item === "node" || "element" in value && typeof value.element === "string";
    });
  });
}

export function compatiblePorts(source: { shape: number[] }, target: { shape: number[] }) {
  return source.shape.length === target.shape.length && target.shape.every((dimension, index) => dimension === 0 || dimension === source.shape[index]);
}
