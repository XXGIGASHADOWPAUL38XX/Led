import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "OnsetStrength",
  "title": "Onset Strength",
  "description": "Detect spectral attacks above a moving noise floor.",
  "category": "features",
  "fields": [
    {
      "name": "amplitudes",
      "control": "port"
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
