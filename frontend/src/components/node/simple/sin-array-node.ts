import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SinArray",
  "title": "Sin Array",
  "description": "Generate a sampled sine wave for spatial modulation.",
  "category": "simple",
  "fields": [
    {
      "name": "number_cycle",
      "control": "slider"
    },
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "center",
      "control": "slider"
    },
    {
      "name": "offset",
      "control": "slider"
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
