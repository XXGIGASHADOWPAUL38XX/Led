import type { Endpoint, NodeDescriptor } from "../../lib/backend/protocol.ts";
import { compatiblePorts } from "../../lib/nodes/configuration.ts";

export const terminalKey = (endpoint: Endpoint, direction: "input" | "output") => JSON.stringify([endpoint.nodeId, endpoint.element, direction]);

export function compatibleTerminals(nodes: NodeDescriptor[], endpoint: Endpoint, direction: "input" | "output") {
  const origin = nodes.find((node) => node.id === endpoint.nodeId)?.ports.find((port) => port.name === endpoint.element);
  const keys = new Set<string>();
  if (!origin) return keys;
  for (const node of nodes) if (node.id !== endpoint.nodeId) {
    for (const port of node.ports) if (port.direction === (direction === "output" ? "in" : "out") && (direction === "output" ? compatiblePorts(origin, port) : compatiblePorts(port, origin))) {
      keys.add(terminalKey({ nodeId: node.id, element: port.name }, port.direction === "out" ? "output" : "input"));
    }
  }
  return keys;
}
