import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "LinearAmplitudesTransformer",
  "title": "Linear Amplitudes Transformer",
  "description": "Apply optional triangular correlation and an exponent to a spectrum.",
  "category": "amplitudes",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "correlation_offset",
      "control": "slider"
    },
    {
      "name": "correlation_step",
      "control": "slider"
    },
    {
      "name": "powering",
      "control": "slider",
      "label": "Weighting"
    },
    {
      "name": "log",
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
