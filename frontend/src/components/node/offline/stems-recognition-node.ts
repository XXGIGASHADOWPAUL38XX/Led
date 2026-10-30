import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "StemsRecognition",
  "title": "Stems Recognition",
  "description": "Analyze complete tracks for recurring spectral groups and presence.",
  "category": "offline",
  "fields": [
    {
      "name": "analysis_nb_frames",
      "control": "slider"
    },
    {
      "name": "similarity_threshold",
      "control": "slider"
    },
    {
      "name": "level_threshold",
      "control": "slider"
    },
    {
      "name": "min_presence_count",
      "control": "slider"
    },
    {
      "name": "hop_ms",
      "control": "slider",
      "unit": "ms"
    }
  ],
  "views": [
    {
      "kind": "trigger",
      "data": "stem_0",
      "label": "Stem 0",
      "open": true
    }
  ]
} satisfies NodeDefinition;
