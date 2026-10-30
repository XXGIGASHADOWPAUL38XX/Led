import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "GroupNode",
  "title": "Group",
  "description": "Own related processing nodes and expose their pipeline outputs.",
  "category": "groups",
  "fields": [
    {
      "name": "nodes",
      "control": "sequence",
      "item": "node"
    },
    {
      "name": "auto_start_nodes",
      "control": "sequence",
      "item": "node"
    }
  ],
  "views": []
} satisfies NodeDefinition;
