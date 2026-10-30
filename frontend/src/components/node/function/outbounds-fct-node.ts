import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "OutboundsFct",
  "title": "Outbounds Fct",
  "description": "Generate a nonnegative mirrored edge-to-center intensity profile.",
  "category": "function",
  "fields": [
    {
      "name": "y_outbound",
      "control": "slider"
    },
    {
      "name": "y_center",
      "control": "slider"
    },
    {
      "name": "y_offset",
      "control": "slider"
    },
    {
      "name": "cute_side_mode",
      "control": "select",
      "label": "Cut side"
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
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
