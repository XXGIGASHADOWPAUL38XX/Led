import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Clip",
  "title": "Clip",
  "description": "Clamp an array to a fixed numeric range.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "min_value",
      "control": "slider"
    },
    {
      "name": "max_value",
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
