"use client";

import { useEffect, useMemo, useRef } from "react";
import { backend } from "@/lib/backend/store";
import type { ViewSettings } from "@/lib/backend/template";
import type { ViewDefinition } from "../node/definition";
import { drawStream, samples } from "./canvas-renderer";
import { drawClustering } from "./clustering-renderer";
import { drawScatter } from "./scatter-renderer";
import { drawAngle } from "./angle-renderer";
import { ScatterTrail } from "./scatter-trail";
import type { ClusteringInput } from "@/lib/nodes/clustering";

/** Frame notifications only schedule a draw; React handles configuration changes. */
export function StreamCanvas({ nodeId, view, settings, title, inputs, dimensions }: {
  nodeId: string; view: ViewDefinition; settings: ViewSettings; title: string; inputs?: ClusteringInput[]; dimensions?: number;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const history = useRef<number[][]>([]);
  const previous = useRef<unknown>(null);
  const camera = useRef([-.7, .45]);
  const trail = useMemo(() => new ScatterTrail(), [nodeId, view.kind, view.data, view.status, dimensions]);
  useEffect(() => {
    const element = canvas.current!;
    const ctx = element.getContext("2d");
    if (!ctx) return;
    let frame = 0, visible = true;
    const draw = () => {
      frame = 0;
      const width = element.clientWidth, height = element.clientHeight;
      if (!width || !height) return;
      const ratio = window.devicePixelRatio || 1;
      const pixelsWide = Math.round(width * ratio), pixelsHigh = Math.round(height * ratio);
      if (element.width !== pixelsWide) element.width = pixelsWide;
      if (element.height !== pixelsHigh) element.height = pixelsHigh;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      if (view.kind === "clustering") drawClustering(ctx, width, height, backend.array(nodeId, view.data!), inputs ?? []);
      else if (view.kind === "angle") drawAngle(ctx, width, height, backend.array(nodeId, view.data!));
      else if (view.kind === "scatter") drawScatter(ctx, width, height, backend.array(nodeId, view.data!),
        backend.array(nodeId, view.status!), trail.points, settings, camera.current);
      else drawStream(ctx, width, height, backend.array(nodeId, view.data!),
        view.colors ? backend.array(nodeId, view.colors) : null, view, settings, history.current);
    };
    const schedule = () => { if (visible && !frame) frame = requestAnimationFrame(draw); };
    const update = () => {
      const value = backend.array(nodeId, view.data!);
      if (view.kind === "scatter") {
        const ready = backend.array(nodeId, view.status!);
        trail.update(value, Number(ready?.data[1]) === 1, settings.historyLength ?? 100);
      }
      if (view.kind === "meter" && value !== null && value !== previous.current) {
        const data = samples(value);
        history.current = Array.from({ length: view.series?.length ?? 1 }, (_, row) => {
          const values = history.current[row] ?? [];
          values.push(Number(data[view.series ? row : data.length - 1] ?? 0));
          return values;
        });
        previous.current = value;
      }
      if (view.kind === "meter") for (const values of history.current) values.splice(0, Math.max(0, values.length - (settings.historyLength ?? 100)));
      schedule();
    };
    const unsubscribe = backend.watchArray(nodeId, view.data!, update);
    const unsubscribeColors = view.colors && view.colors !== view.data ? backend.watchArray(nodeId, view.colors, schedule) : undefined;
    const unsubscribeStatus = view.status ? backend.watchArray(nodeId, view.status, update) : undefined;
    let drag: { x: number; y: number; id: number } | null = null;
    const down = (event: PointerEvent) => {
      if (dimensions !== 3 || event.button !== 0) return;
      event.preventDefault(); event.stopPropagation(); element.setPointerCapture(event.pointerId);
      drag = { x: event.clientX, y: event.clientY, id: event.pointerId };
    };
    const move = (event: PointerEvent) => {
      if (!drag || event.pointerId !== drag.id) return;
      event.stopPropagation();
      camera.current[0] += (event.clientX - drag.x) * .01;
      camera.current[1] = Math.max(-1.5, Math.min(1.5, camera.current[1] + (event.clientY - drag.y) * .01));
      drag.x = event.clientX; drag.y = event.clientY; schedule();
    };
    const up = () => { drag = null; };
    element.addEventListener("pointerdown", down); element.addEventListener("pointermove", move);
    element.addEventListener("pointerup", up); element.addEventListener("pointercancel", up);
    element.addEventListener("lostpointercapture", up);
    const resize = new ResizeObserver(schedule);
    resize.observe(element);
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) schedule();
      else { cancelAnimationFrame(frame); frame = 0; }
    });
    visibility.observe(element);
    update();
    return () => {
      unsubscribe(); unsubscribeColors?.(); unsubscribeStatus?.(); resize.disconnect(); visibility.disconnect(); cancelAnimationFrame(frame);
      element.removeEventListener("pointerdown", down); element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerup", up); element.removeEventListener("pointercancel", up);
      element.removeEventListener("lostpointercapture", up);
    };
  }, [nodeId, view, settings, inputs, dimensions, trail]);
  return <canvas ref={canvas} role="img" aria-label={title}
    className={`block w-full ${dimensions === 3 ? "touch-none cursor-grab active:cursor-grabbing" : ""} ${view.kind === "clustering" || view.kind === "scatter" || view.kind === "angle" ? "aspect-square" : view.kind === "color" ? "h-14" : view.kind === "trigger" ? "h-10" : "h-36"}`} />;
}
