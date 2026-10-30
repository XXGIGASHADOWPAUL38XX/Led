import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Routing",
  "title": "Routing",
  "description": "Placeholder for routing a configured list of operator nodes.",
  "category": "routing",
  "fields": [
    {
      "name": "operator_nodes",
      "control": "sequence",
      "item": "node"
    }
  ],
  "views": []
} satisfies NodeDefinition;
