import dagre from "@dagrejs/dagre";
import type { Graph } from "../../lib/backend/protocol.ts";

export type NodeSize = { width: number; height: number };

/** Fast layered layout; measurements and positions use the same top-left origin. */
export function layoutGraph(graph: Graph, sizes: ReadonlyMap<string, NodeSize>): Record<string, [number, number]> {
  const layout = new dagre.graphlib.Graph().setGraph({ rankdir: "LR", ranker: "longest-path", nodesep: 48, ranksep: 100, marginx: 24, marginy: 24 }).setDefaultEdgeLabel(() => ({}));
  for (const node of graph.nodes) layout.setNode(node.id, { ...sizes.get(node.id)! });
  for (const edge of graph.connections) layout.setEdge(edge.source.nodeId, edge.target.nodeId);
  dagre.layout(layout);
  return Object.fromEntries(graph.nodes.map(({ id }) => {
    const { x, y, width, height } = layout.node(id);
    return [id, [Math.round(x - width / 2), Math.round(y - height / 2)]];
  }));
}
