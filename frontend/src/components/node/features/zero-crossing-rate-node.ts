import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ZeroCrossingRate",
  "title": "Zero Crossing Rate",
  "description": "Measure waveform sign changes as a rough noisiness feature.",
  "category": "features",
  "fields": [
    {
      "name": "buffer_data",
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
