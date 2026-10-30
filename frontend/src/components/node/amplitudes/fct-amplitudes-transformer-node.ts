import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "FctAmplitudesTransformer",
  "title": "Fct Amplitudes Transformer",
  "description": "Shape a spectrum with a supplied amplitude-level function.",
  "category": "amplitudes",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "powering",
      "control": "slider",
      "label": "Weighting"
    },
    {
      "name": "log",
      "control": "slider"
    },
    {
      "name": "amplitudes_level_fct",
      "control": "node-reference",
      "matchInput": "input_data",
      "nodeTypes": [
        "AmplitudeLevelFunction"
      ]
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
