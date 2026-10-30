import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "RMS",
  "title": "RMS",
  "description": "Measure overall audio level with root mean square amplitude.",
  "category": "auditory",
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
      "label": "RMS",
      "open": true
    }
  ]
} satisfies NodeDefinition;
