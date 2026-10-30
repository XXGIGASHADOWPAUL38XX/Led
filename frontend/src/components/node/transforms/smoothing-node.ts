import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "Smoothing",
  "title": "Smoothing",
  "description": "Wrap a history window and aggregation function for signal smoothing.",
  "category": "transforms",
  "fields": [
    {
      "name": "input_value",
      "control": "port"
    },
    {
      "name": "length",
      "control": "slider",
      "rebuild": true
    },
    {
      "name": "window_function",
      "control": "node-reference",
      "nodeTypes": [
        "AveragedWindowFct",
        "CeilWindowFct",
        "DecreasingAvgWindowFct",
        "MinWindowFct",
        "MaxWindowFct",
        "SumWindowFct"
      ]
    },
    {
      "name": "avg_axis",
      "control": "axis",
      "label": "Reduction axes"
    },
    {
      "name": "offset",
      "control": "slider"
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
