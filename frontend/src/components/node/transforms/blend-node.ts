import type { NodeDefinition } from "../definition.ts";

export default {
  type: "Blend",
  title: "Blend",
  description: "Blend values or broadcast-compatible arrays: sum(value × weight) / sum(weights). Drop wires to add inputs. Zero total weight outputs zero.",
  category: "transforms",
  fields: [{ name: "inputs", control: "blend", label: "Inputs", rebuild: true, addPort: "add_element" }],
  views: [{ kind: "bars", data: "data", label: "Blend", open: true }],
} satisfies NodeDefinition;
