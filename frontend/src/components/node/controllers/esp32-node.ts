import type { NodeDefinition } from "../definition.ts";

export default {
  "type": "ESP32",
  "title": "ESP32",
  "description": "Send an RGBA strip to an ESP32 over UDP using DDP.",
  "category": "controllers",
  "fields": [
    {
      "name": "rgba",
      "control": "port"
    },
    {
      "name": "power_log",
      "control": "slider"
    },
    {
      "name": "min_alpha",
      "control": "slider"
    },
    {
      "name": "remove_alpha",
      "control": "slider"
    },
    {
      "name": "esp32_ip",
      "control": "text",
      "label": "Device address"
    },
    {
      "name": "ddp_port",
      "control": "slider",
      "unit": ""
    },
    {
      "name": "led_count",
      "control": "slider"
    }
  ],
  "views": []
} satisfies NodeDefinition;
