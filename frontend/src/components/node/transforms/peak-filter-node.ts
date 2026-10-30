import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "PeakFilter",
  "title": "Peak Filter",
  "description": "Keep only the strongest local peaks in a vector.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "peaks_to_keep",
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
