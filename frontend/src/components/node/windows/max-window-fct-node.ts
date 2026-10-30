import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "MaxWindowFct",
  "title": "Max Window Fct",
  "description": "Compute the maximum of a WindowNode history.",
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
