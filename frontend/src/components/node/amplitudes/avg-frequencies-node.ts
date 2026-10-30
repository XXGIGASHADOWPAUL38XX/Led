import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "AvgFrequencies",
  "title": "Avg Frequencies",
  "description": "Compute the amplitude-weighted average frequency.",
  "category": "amplitudes",
  "fields": [
    {
      "name": "input_frequencies",
      "control": "port"
    },
    {
      "name": "input_amplitudes",
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
