import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "RGBAPipeline",
  "title": "RGBAPipeline",
  "description": "Combine per-position RGB colors and normalized opacity.",
  "category": "visual",
  "fields": [
    { "name": "number_points", "control": "slider", "label": "Points", "rebuild": true },
    {
      "name": "rgb",
      "control": "port"
    },
    {
      "name": "alpha",
      "control": "port"
    }
  ],
  "views": [
    {
      "kind": "color",
      "data": "rgba",
      "label": "Rgba",
      "open": true
    }
  ]
} satisfies NodeDefinition;
