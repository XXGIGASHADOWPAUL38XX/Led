import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ValueTransformer",
  "title": "Value Transformer",
  "description": "Map numeric arrays between intervals, preserving an editable, adaptive shape.",
  "category": "transforms",
  "fields": [
    { "name": "shape", "control": "shape", "label": "Input shape", "rebuild": true },
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "input_value_interval",
      "control": "interval",
      "ordered": false,
      "label": "Input range",
      "min": -10000,
      "max": 10000
    },
    {
      "name": "output_value_interval",
      "control": "interval",
      "ordered": false,
      "label": "Output range",
      "min": -10000,
      "max": 10000
    }
  ],
  "views": [
    {
      "kind": "meter",
      "data": "output_value",
      "label": "Output value",
      "open": false
    }
  ]
} satisfies NodeDefinition;
