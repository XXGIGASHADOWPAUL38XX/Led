import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Difference",
  "title": "Difference",
  "description": "Subtract matching vectors and clip their difference to [0, 1].",
  "category": "transforms",
  "fields": [
    {
      "name": "a",
      "control": "port"
    },
    {
      "name": "b",
      "control": "port"
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "diff",
      "label": "Diff",
      "open": true
    }
  ]
} satisfies NodeDefinition;
