import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Function",
  "title": "Function",
  "description": "Generate a curve with editable points, segment slopes, and live control inputs.",
  "category": "function",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    },
    {
      "name": "points",
      "control": "curve",
      "portsPrefix": "point_"
    },
    { "name": "slopes", "control": "array", "hidden": true },
    { "name": "point_ids", "control": "managed", "hidden": true },
    { "name": "controls", "control": "managed", "hidden": true }
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
