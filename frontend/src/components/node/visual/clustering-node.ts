import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Clustering",
  "title": "Clustering",
  "description": "Track scalar parameters on crossing horizontal and vertical grid lines, each with its own interval.",
  "category": "visual",
  "fields": [
    {
      "name": "inputs",
      "control": "clustering",
      "label": "Parameters",
      "rebuild": true,
      "addPort": "add_element"
    }
  ],
  "views": [
    {
      "kind": "clustering",
      "data": "data",
      "label": "Clustering",
      "open": true
    }
  ]
} satisfies NodeDefinition;
