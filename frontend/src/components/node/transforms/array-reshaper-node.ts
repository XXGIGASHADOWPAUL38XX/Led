import type { NodeDefinition } from "../definition.ts";

export default {
  type: "ArrayReshaper",
  title: "Array Reshaper",
  description: "Slice → reshape → transpose → reverse. Slice includes start and excludes end; reshape must preserve the selected element count. Negative axes count from the end.",
  category: "transforms",
  fields: [
    { name: "input_data", control: "port", label: "Input data" },
    { name: "shape", control: "shape", label: "Input shape", rebuild: true },
    { name: "slice_interval", control: "interval", label: "Slice", step: 1, ordered: false, rebuild: true },
    { name: "slice_axis", control: "slider", label: "Slice axis", rebuild: true },
    { name: "reshape", control: "shape", label: "Reshape", rebuild: true },
    { name: "transpose", control: "switch", label: "Transpose", rebuild: true },
    { name: "transpose_axes", control: "axis", label: "Custom transpose axes", permutation: true, rebuild: true },
    { name: "reverse", control: "switch", label: "Reverse", rebuild: true },
    { name: "reverse_axis", control: "slider", label: "Reverse axis", rebuild: true },
  ],
  views: [{ kind: "bars", data: "data", label: "Data", open: true }],
} satisfies NodeDefinition;
