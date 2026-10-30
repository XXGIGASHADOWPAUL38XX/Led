import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ValueTransformer",
  "title": "Value Transformer",
  "description": "Map scalar or vector values between numeric intervals.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "input_value_interval",
      "control": "interval",
      "label": "Input range",
      "min": -10000,
      "max": 10000
    },
    {
      "name": "output_value_interval",
      "control": "interval",
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
