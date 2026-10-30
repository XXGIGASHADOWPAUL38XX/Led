"use client";

import { useState } from "react";
import { Node } from "../node/node";
import { SliderElement } from "../elements/slider-element";
import { SwitchElement } from "../elements/switch-element";
import { SelectElement } from "../elements/select-element";

const presets = [
  { value: "512", label: "Fast · 512" },
  { value: "2048", label: "Balanced · 2048" },
  { value: "4096", label: "Detailed · 4096" },
];

export function BufferPreview() {
  const [length, setLength] = useState(2048);
  const [enabled, setEnabled] = useState(true);
  return (
    <Node id="buffer-1" title="Buffer" description="Keep a rolling stereo audio window for analysis." inputs={["indata"]} outputs={["data"]}>
      <SwitchElement label="Enabled" checked={enabled} onCheckedChange={setEnabled} />
      <SelectElement label="Preset" value={presets.some((preset) => preset.value === String(length)) ? String(length) : ""} disabled={!enabled} placeholder="Custom"
        options={presets}
        onValueChange={(value) => setLength(Number(value))} />
      <SliderElement label="Length" value={length} onValueChange={setLength} min={1} max={4096} step={1} unit="samples" disabled={!enabled} />
    </Node>
  );
}
