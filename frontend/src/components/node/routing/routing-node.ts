import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Routing",
  "title": "Routing",
  "description": "Enable the strongest scalar source; silence disables all routes.",
  "category": "routing",
  "fields": [
    {
      "name": "operator_nodes",
      "control": "sequence",
      "label": "Sources",
      "item": "node"
    }
  ],
  "views": [
    { "kind": "bars", "data": "data", "label": "Active route", "open": true },
    { "kind": "meter", "data": "level", "label": "Band level", "open": false }
  ]
} satisfies NodeDefinition;
