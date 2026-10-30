import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Function",
  "title": "Function",
  "description": "Generate an editable piecewise-linear spatial curve.",
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
      "control": "curve"
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
