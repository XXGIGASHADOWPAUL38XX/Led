import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Trigger",
  "title": "Trigger",
  "description": "Emit a one-update pulse when the last input value crosses a condition.",
  "category": "trigger",
  "fields": [
    {
      "name": "input_data",
      "control": "port"
    },
    {
      "name": "trigger_mode",
      "control": "select"
    },
    {
      "name": "threshold",
      "control": "slider"
    }
  ],
  "views": [
    {
      "kind": "trigger",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
