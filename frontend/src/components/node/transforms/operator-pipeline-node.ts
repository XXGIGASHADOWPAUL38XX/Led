import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "OperatorPipeline",
  "title": "Operator Pipeline",
  "description": "Evaluate an expression assembled from Elements and literal tokens.",
  "category": "transforms",
  "fields": [
    { "name": "operations", "control": "managed", "hidden": true },
    { "name": "input_names", "control": "managed", "hidden": true },
    {
      "name": "arguments",
      "control": "expression",
      "addPort": "add_element",
      "item": "token"
    },
    {
      "name": "length",
      "hidden": true,
      "control": "slider",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": false
    }
  ]
} satisfies NodeDefinition;
