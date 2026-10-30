"use client";

import { type RefObject, useCallback, useEffect, useRef } from "react";
import type { Point } from "./connection-path";

export type CanvasHandle = { insertionPosition: () => [number, number] };
export type CanvasDrag = {
  toCanvas: (x: number, y: number) => Point;
  startNodeDrag: (x: number, y: number, update: (point: Point) => void) => void;
  moveNodeDrag: (x: number, y: number) => void;
  endNodeDrag: (x: number, y: number) => Point;
  cancelNodeDrag: () => void;
};

/** All pointer positions use canvas coordinates, including while the viewport pans. */
export function useCanvasViewport(viewport: RefObject<HTMLDivElement | null>, canvas: RefObject<HTMLDivElement | null>, zoom: number) {
  const pointer = useRef<Point | null>(null);
  const drag = useRef<{ pointer: Point; update: (point: Point) => void } | null>(null);
  const frame = useRef(0);
  const toCanvas = useCallback((x: number, y: number) => {
    const rect = canvas.current!.getBoundingClientRect();
    return { x: (x - rect.left) / zoom, y: (y - rect.top) / zoom };
  }, [canvas, zoom]);
  const insertionPosition = useCallback((): [number, number] => {
    const rect = viewport.current!.getBoundingClientRect();
    const cursor = pointer.current ?? { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 };
    const position = toCanvas(cursor.x, cursor.y);
    return [position.x, position.y];
  }, [viewport, toCanvas]);
  const rememberPointer = useCallback((x: number, y: number) => { pointer.current = { x, y }; }, []);
  const cancelNodeDrag = useCallback(() => { cancelAnimationFrame(frame.current); frame.current = 0; drag.current = null; }, []);
  const moveNodeDrag = useCallback((x: number, y: number) => {
    if (!drag.current) return;
    drag.current.pointer = { x, y };
    drag.current.update(toCanvas(x, y));
  }, [toCanvas]);
  const startNodeDrag = useCallback((x: number, y: number, update: (point: Point) => void) => {
    cancelNodeDrag();
    drag.current = { pointer: { x, y }, update };
    const step = () => {
      const current = drag.current;
      if (!current) return;
      const element = viewport.current!, rect = element.getBoundingClientRect();
      const speed = (position: number, low: number, high: number) => 12 * (Math.min(1, Math.max(0, (position - high + 48) / 48)) - Math.min(1, Math.max(0, (low + 48 - position) / 48)));
      const left = element.scrollLeft, top = element.scrollTop;
      element.scrollBy(speed(current.pointer.x, Math.max(0, rect.left), Math.min(window.innerWidth, rect.right)), speed(current.pointer.y, Math.max(0, rect.top), Math.min(window.innerHeight, rect.bottom)));
      if (left !== element.scrollLeft || top !== element.scrollTop) current.update(toCanvas(current.pointer.x, current.pointer.y));
      frame.current = requestAnimationFrame(step);
    };
    frame.current = requestAnimationFrame(step);
  }, [viewport, cancelNodeDrag, toCanvas]);
  const endNodeDrag = useCallback((x: number, y: number) => {
    const position = toCanvas(x, y);
    cancelNodeDrag();
    return position;
  }, [toCanvas, cancelNodeDrag]);
  useEffect(() => {
    window.addEventListener("pointerup", cancelNodeDrag);
    window.addEventListener("pointercancel", cancelNodeDrag);
    return () => { cancelNodeDrag(); window.removeEventListener("pointerup", cancelNodeDrag); window.removeEventListener("pointercancel", cancelNodeDrag); };
  }, [cancelNodeDrag]);
  return { toCanvas, insertionPosition, rememberPointer, startNodeDrag, moveNodeDrag, endNodeDrag, cancelNodeDrag };
}
