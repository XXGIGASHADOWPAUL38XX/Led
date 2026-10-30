"use client";

import { useArray, useGraph } from "@/lib/backend/hooks";
import { ColorElement, type ColorElementProps } from "../elements/color-element";
import { Terminal } from "../workspace/terminal";

/** Stream driven channels without publishing control metadata every frame. */
export function ColorControl({ nodeId, colorPort, channels, ...props }: ColorElementProps & { nodeId: string; colorPort: string; channels: string[] }) {
  const snapshot = useGraph();
  const red = useArray(nodeId, channels[0]), green = useArray(nodeId, channels[1]), blue = useArray(nodeId, channels[2]);
  const rgb = useArray(nodeId, colorPort);
  const arrays = [red, green, blue];
  const linked = (index: number) => snapshot?.graph.connections.some((edge) => edge.target.nodeId === nodeId && edge.target.element === channels[index]) ?? false;
  const wholeLinked = snapshot?.graph.connections.some((edge) => edge.target.nodeId === nodeId && edge.target.element === colorPort);
  const base = wholeLinked && rgb ? Array.from(rgb.data, Number) : props.value;
  const value = base.map((channel, index) => Math.max(0, Math.min(255, linked(index) && arrays[index] ? Number(arrays[index]!.data[0]) : channel))) as unknown as ColorElementProps['value'];
  return <ColorElement {...props} value={value} channelDisabled={linked} renderTerminal={nodeId ? (index) => <Terminal endpoint={{ nodeId, element: channels[index] }} direction="input" className="absolute -left-5 top-3" /> : undefined} />;
}
