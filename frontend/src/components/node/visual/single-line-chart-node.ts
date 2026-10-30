import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SingleLineChart",
  "title": "Single Line Chart",
  "description": "Plot a selected Element's latest scalar value over time.",
  "category": "visual",
  "fields": [
    {
      "name": "input_data",
      "control": "reference"
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
