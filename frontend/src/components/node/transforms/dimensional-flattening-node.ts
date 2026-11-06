import type { NodeDefinition } from "../definition.ts";

export default {
  type: "DimensionalFlattening",
  title: "Dimensional Flattening",
  description: "NMF coordinates with configurable dimensions: XY plot, rotatable XYZ plot, or the shared axis grid for 4+. Changing dimensions starts fresh calibration.",
  category: "transforms",
  fields: [
    { name: "shape", control: "shape", label: "Input shape", rebuild: true },
    { name: "input_data", control: "port" },
    { name: "dimensions", control: "slider", label: "Dimensions", rebuild: true, step: 1 },
    { name: "calibration_samples", control: "slider", label: "Calibration samples" },
    { name: "model_path", control: "text", label: "Saved model path", rebuild: true },
  ],
  actions: ["recalibrate"],
  views: [
    { kind: "scatter", data: "data", status: "calibration", label: "Feature space · NMF", open: true },
    { kind: "meter", data: "x", label: "X", open: false },
    { kind: "meter", data: "y", label: "Y", open: false },
    { kind: "meter", data: "z", label: "Z", open: false },
  ],
} satisfies NodeDefinition;
