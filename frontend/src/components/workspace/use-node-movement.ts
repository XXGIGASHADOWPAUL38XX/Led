import { useCallback, useRef, type RefObject } from "react";
import { backend } from "@/lib/backend/store";
import type { Graph } from "@/lib/backend/protocol";
import type { Point } from "./connection-path";
import type { ObjectSelection } from "./object-selection";

export function useNodeMovement(graph: Graph, container: RefObject<HTMLDivElement | null>, selection: ObjectSelection, invalidate: () => void) {
  const active = useRef<{ id: string; nodes: { id: string; element: HTMLElement; position: [number, number] }[] } | null>(null);
  const beginNodeMove = useCallback((id: string) => {
    const ids = selection.kind === "node" && selection.ids.has(id) ? selection.ids : new Set([id]);
    const elements = new Map([...container.current!.querySelectorAll<HTMLElement>("[data-node-id]")].map((node) => [node.dataset.nodeId!, node]));
    active.current = { id, nodes: graph.nodes.filter((node) => ids.has(node.id)).map((node) => ({ id: node.id, position: node.position, element: elements.get(node.id)! })) };
  }, [graph, container, selection]);
  const updateNodeMove = useCallback((point: Point) => {
    if (!active.current) return {};
    const { nodes, id } = active.current;
    const origin = nodes.find((node) => node.id === id)!.position;
    const positions = Object.fromEntries(nodes.map((node) => {
      const position: [number, number] = [node.position[0] + point.x - origin[0], node.position[1] + point.y - origin[1]];
      node.element.style.transform = `translate(${position[0]}px, ${position[1]}px)`;
      return [node.id, position];
    }));
    invalidate();
    return positions;
  }, [invalidate]);
  const cancelNodeMove = useCallback(() => {
    for (const node of active.current?.nodes ?? []) node.element.style.transform = `translate(${node.position[0]}px, ${node.position[1]}px)`;
    active.current = null;
    invalidate();
  }, [invalidate]);
  const commitNodeMove = useCallback(async (point: Point) => {
    const original = active.current;
    if (!original) return;
    const positions = updateNodeMove(point);
    active.current = null;
    if (original.nodes.every((node) => node.position.every((coordinate, index) => coordinate === positions[node.id][index]))) return;
    if (await backend.command("graph.move", { positions }) === undefined) {
      for (const node of original.nodes) node.element.style.transform = `translate(${node.position[0]}px, ${node.position[1]}px)`;
      invalidate();
    }
  }, [updateNodeMove, invalidate]);
  return { beginNodeMove, updateNodeMove, commitNodeMove, cancelNodeMove };
}
export type NodeMovement = ReturnType<typeof useNodeMovement>;
