import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "HighFilter",
  "title": "High Filter",
  "description": "Apply a first-order Butterworth high-pass filter to audio. Input shape adapts when linked and is editable.",
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
      "name": "highpass_freq",
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
