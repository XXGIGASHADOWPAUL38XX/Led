import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "FreqScaledAmplitudesTransformer",
  "title": "Freq Scaled Amplitudes Transformer",
  "description": "Aggregate spectrum neighborhoods with index-dependent widths.",
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
      "name": "correlation_weight_min",
      "control": "slider",
      "scale": "logarithmic"
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
