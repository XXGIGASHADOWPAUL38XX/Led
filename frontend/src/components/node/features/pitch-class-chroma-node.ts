import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "PitchClassChroma",
  "title": "Pitch Class Chroma",
  "description": "Fold spectral amplitudes into twelve pitch classes across octaves.",
  "category": "features",
  "fields": [
    {
      "name": "amplitudes",
      "control": "port"
    },
    {
      "name": "frequencies",
      "control": "port"
    },
    {
      "name": "reference_frequency",
      "control": "slider",
      "unit": "Hz"
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
