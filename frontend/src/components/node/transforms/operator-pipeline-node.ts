import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "OperatorPipeline",
  "title": "Operator Pipeline",
  "description": "Evaluate an expression assembled from Elements and literal tokens.",
  "category": "transforms",
  "fields": [
    {
      "name": "arguments",
      "control": "sequence",
      "item": "token"
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
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
