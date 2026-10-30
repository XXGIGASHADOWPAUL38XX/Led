import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "MinWindowFct",
  "title": "Min Window Fct",
  "description": "Compute the minimum of a WindowNode history.",
  "category": "windows",
  "fields": [
    {
      "name": "window",
      "control": "reference",
      "nodeTypes": [
        "Window"
      ]
    },
    {
      "name": "avg_axis",
      "control": "axis",
      "label": "Reduction axes"
    }
  ],
  "views": [
    {
      "kind": "meter",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
