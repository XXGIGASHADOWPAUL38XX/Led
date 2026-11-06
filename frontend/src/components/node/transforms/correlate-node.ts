import type { NodeDefinition } from "../definition.ts";

export default {
  type: "Correlate",
  title: "Correlate",
  description: "Spread peaks or blend neighboring colors with triangular weights, preserving RGB channels.",
  category: "transforms",
  fields: [
    { name: "shape", control: "shape", label: "Input shape", rebuild: true },
    { name: "input_data", control: "port" },
    { name: "mode", control: "select", label: "Mode" },
    { name: "correlation_offset", label: "Spread strength", control: "slider", step: 0.001 },
    { name: "correlation_step", label: "Span fraction", control: "slider", step: 0.001 },
  ],
  views: [{ kind: "bars", data: "data", label: "Data", open: false }],
} satisfies NodeDefinition;
