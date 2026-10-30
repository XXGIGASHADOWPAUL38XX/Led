import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "CrestFactor",
  "title": "Crest Factor",
  "description": "Measure waveform peak relative to RMS for transient detection.",
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
