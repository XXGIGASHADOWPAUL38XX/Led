import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "LowFilter",
  "title": "Low Filter",
  "description": "Apply a first-order Butterworth low-pass filter to audio. Input shape adapts when linked and is editable.",
  "category": "auditory",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "shape",
      "control": "shape",
      "label": "Input shape",
      "rebuild": true
    },
    {
      "name": "lowpass_freq",
      "control": "slider",
      "unit": "Hz"
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
