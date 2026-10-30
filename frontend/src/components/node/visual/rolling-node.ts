import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "RollingNode",
  "title": "Rolling",
  "description": "Rotate a color or data array cyclically along its first axis.",
  "category": "visual",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "roll_speed",
      "control": "slider"
    }
  ],
  "views": [
    {
      "kind": "color",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
