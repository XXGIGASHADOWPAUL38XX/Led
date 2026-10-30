import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SnareDecay",
  "title": "Snare Decay",
  "description": "Combine band energy and spectral change into a trigger pipeline.",
  "category": "groups",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "min_frequency",
      "control": "slider",
      "label": "Min frequency",
      "unit": "Hz",
      "scale": "logarithmic"
    },
    {
      "name": "max_frequency",
      "control": "slider",
      "label": "Max frequency",
      "unit": "Hz",
      "scale": "logarithmic"
    },
    {
      "name": "threshold",
      "control": "slider"
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
