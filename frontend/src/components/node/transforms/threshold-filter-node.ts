import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ThresholdFilter",
  "title": "Threshold Filter",
  "description": "Suppress array values below a threshold.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "threshold",
      "control": "slider"
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
