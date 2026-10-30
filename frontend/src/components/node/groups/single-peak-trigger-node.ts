import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SinglePeakTrigger",
  "title": "Single Peak Trigger",
  "description": "Isolate the strongest spectral peak above its recent average.",
  "category": "groups",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "window_length",
      "control": "slider",
      "scale": "logarithmic",
      "rebuild": true
    },
    {
      "name": "threshold",
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
