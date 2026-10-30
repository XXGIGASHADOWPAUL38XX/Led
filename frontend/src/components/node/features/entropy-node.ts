import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Entropy",
  "title": "Entropy",
  "description": "Measure how evenly spectral amplitude is distributed.",
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
