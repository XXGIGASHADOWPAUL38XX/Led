import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "SinPeriodicity",
  "title": "Sin Periodicity",
  "description": "Analyze sinusoidal periodicity from an audio buffer.",
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
      "label": "Periodicity",
      "open": true
    }
  ]
} satisfies NodeDefinition;
