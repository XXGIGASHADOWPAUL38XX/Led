import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "KickDecay",
  "title": "Kick Decay",
  "description": "Detect low-frequency attacks and produce a decaying intensity signal.",
  "category": "groups",
  "fields": [
    {
      "name": "buffer_data",
      "control": "port"
    },
    {
      "name": "lowpass_freq",
      "control": "slider",
      "unit": "Hz"
    },
    {
      "name": "threshold",
      "control": "slider"
    },
    {
      "name": "decay_length",
      "control": "slider",
      "scale": "logarithmic",
      "rebuild": true
    }
  ],
  "views": [
    {
      "kind": "meter",
      "data": "data",
      "label": "Data",
      "open": true
    }
  ]
} satisfies NodeDefinition;
