import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "CosineAngle",
  "title": "Cosine Angle",
  "description": "Convert (N, 2) XY coordinates to angles in radians. Display each direction on a circle of radius 1; the origin uses angle 0.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_data",
      "control": "port",
      "label": "XY coordinates"
    },
    {
      "name": "shape",
      "control": "shape",
      "label": "Input shape",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "angle",
      "data": "data",
      "label": "Direction",
      "unit": "rad",
      "open": true
    }
  ]
} satisfies NodeDefinition;
