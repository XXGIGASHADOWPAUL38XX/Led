import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ChromaPrism",
  "title": "Chroma Prism",
  "description": "Convert spectrum and audio features into animated bars and RGBA colors.",
  "category": "features",
  "fields": [
    {
      "name": "amplitudes",
      "control": "port"
    },
    {
      "name": "chroma",
      "control": "port"
    },
    {
      "name": "spectral_centroid",
      "control": "port"
    },
    {
      "name": "spectral_flux",
      "control": "port"
    },
    {
      "name": "onset_strength",
      "control": "port"
    },
    {
      "name": "entropy",
      "control": "port"
    },
    {
      "name": "zero_crossing_rate",
      "control": "port"
    },
    {
      "name": "crest_factor",
      "control": "port"
    },
    {
      "name": "mid_side_energy",
      "control": "port"
    }
  ],
  "views": [
    {
      "kind": "bars",
      "data": "data",
      "label": "Data",
      "open": true
    },
    {
      "kind": "color",
      "data": "brushes",
      "label": "Brushes",
      "open": false
    }
  ]
} satisfies NodeDefinition;
