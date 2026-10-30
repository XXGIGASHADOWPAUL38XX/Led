import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SingleColor",
  "title": "Single Color",
  "description": "Generate a uniform RGB strip for coloring a visualization.",
  "category": "visual",
  "fields": [
    {
      "name": "color",
      "control": "color"
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
      "kind": "color",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
