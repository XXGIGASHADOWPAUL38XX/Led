import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Gradiant",
  "title": "Gradiant",
  "description": "Generate a spatial RGB gradient by interpolating in HSV color space.",
  "category": "rainbow",
  "fields": [
    {
      "name": "n_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "color_in",
      "control": "color"
    },
    {
      "name": "color_out",
      "control": "color"
    },
    {
      "name": "cycle",
      "control": "slider"
    }
  ],
  "views": [
    {
      "kind": "color",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
