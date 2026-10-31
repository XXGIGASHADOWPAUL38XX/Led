import { useRef, useState, type PointerEvent, type RefObject } from "react";
import type { Point } from "./connection-path";
import type { CanvasDrag } from "./use-canvas-viewport";
import { useObjectSelection } from "./object-selection";

export function useBoxSelection(container: RefObject<HTMLDivElement | null>, canvas: CanvasDrag) {
  const selection = useObjectSelection()!;
  const active = useRef<{ start: Point; base: string[] } | null>(null);
  const [box, setBox] = useState<{ left: number; top: number; width: number; height: number } | null>(null);
  const update = (point: Point) => {
    const { start, base } = active.current!;
    const rect = { left: Math.min(start.x, point.x), top: Math.min(start.y, point.y), width: Math.abs(point.x - start.x), height: Math.abs(point.y - start.y) };
    const ids = [...container.current!.querySelectorAll<HTMLElement>("[data-node-id]")].filter((node) => {
      const bounds = node.getBoundingClientRect();
      const from = canvas.toCanvas(bounds.left, bounds.top), to = canvas.toCanvas(bounds.right, bounds.bottom);
      return to.x >= rect.left && from.x <= rect.left + rect.width && to.y >= rect.top && from.y <= rect.top + rect.height;
    }).map((node) => node.dataset.nodeId!);
    selection.setNodes([...base, ...ids]);
    setBox(rect);
  };
  const cancel = () => { active.current = null; setBox(null); canvas.cancelNodeDrag(); };
  return { box, cancel,
    onPointerDown: (event: PointerEvent<HTMLDivElement>) => {
      if (event.button !== 0 || !event.currentTarget.contains(event.target as Node) || (event.target as Element).closest("[data-node-id], [data-terminal]")) return;
      event.preventDefault();
      event.currentTarget.focus({ preventScroll: true });
      const base = (event.ctrlKey || event.metaKey) && selection.value.kind === "node" ? [...selection.value.ids] : [];
      active.current = { start: canvas.toCanvas(event.clientX, event.clientY), base };
      selection.setNodes(base);
      event.currentTarget.setPointerCapture(event.pointerId);
      canvas.startNodeDrag(event.clientX, event.clientY, update);
    },
    onPointerMove: (event: PointerEvent<HTMLDivElement>) => {
      if (active.current) canvas.moveNodeDrag(event.clientX, event.clientY);
    },
    onPointerUp: (event: PointerEvent<HTMLDivElement>) => {
      if (!active.current) return;
      update(canvas.endNodeDrag(event.clientX, event.clientY));
      cancel();
      event.currentTarget.releasePointerCapture(event.pointerId);
    },
  };
}
