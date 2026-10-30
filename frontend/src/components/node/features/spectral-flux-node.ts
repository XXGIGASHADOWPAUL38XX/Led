import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SpectralFlux",
  "title": "Spectral Flux",
  "description": "Measure positive spectrum change for transient detection.",
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
