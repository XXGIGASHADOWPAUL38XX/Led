import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "LinearAmplitudesTransformer",
  "title": "Linear Amplitudes Transformer",
  "description": "Apply an exponent to a spectrum without changing its source.",
  "category": "amplitudes",
  "fields": [
    { "name": "number_points", "control": "slider", "label": "Points", "rebuild": true },
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
