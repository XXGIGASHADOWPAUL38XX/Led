import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SpectralCentroid",
  "title": "Spectral Centroid",
  "description": "Measure spectral brightness as an amplitude-weighted frequency.",
  "category": "features",
  "fields": [
    {
      "name": "amplitudes",
      "control": "port"
    },
    {
      "name": "frequencies",
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
