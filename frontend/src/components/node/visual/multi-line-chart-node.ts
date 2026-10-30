import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "MultiLineChart",
  "title": "Multi Line Chart",
  "description": "Plot several selected Elements as separate scalar histories.",
  "category": "visual",
  "fields": [
    {
      "name": "node_selectors",
      "control": "sequence",
      "item": "reference"
    },
    {
      "name": "number_points",
      "control": "slider",
      "label": "Points",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "history",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
