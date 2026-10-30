"use client";

import { useEffect, useRef } from "react";
import { backend } from "@/lib/backend/store";
import type { ViewSettings } from "@/lib/backend/template";
import type { ViewDefinition } from "../node/definition";
import { drawStream, samples } from "./canvas-renderer";

/** Frame notifications only schedule a draw; React handles configuration changes. */
export function StreamCanvas({ nodeId, view, settings, title }: {
  nodeId: string; view: ViewDefinition; settings: ViewSettings; title: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const history = useRef<number[]>([]);
  const previous = useRef<unknown>(null);
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
      drawStream(ctx, width, height, backend.array(nodeId, view.data!),
        view.colors ? backend.array(nodeId, view.colors) : null, view, settings, history.current);
    };
    const schedule = () => { if (visible && !frame) frame = requestAnimationFrame(draw); };
    const update = () => {
      const value = backend.array(nodeId, view.data!);
      if (view.kind === "meter" && value !== null && value !== previous.current) {
        const data = samples(value);
        history.current.push(Number(data[data.length - 1] ?? 0));
        previous.current = value;
      }
      history.current = history.current.slice(-(settings.historyLength ?? 100));
      schedule();
    };
    const unsubscribe = backend.watchArray(nodeId, view.data!, update);
    const unsubscribeColors = view.colors && view.colors !== view.data ? backend.watchArray(nodeId, view.colors, schedule) : undefined;
    const resize = new ResizeObserver(schedule);
    resize.observe(element);
    const visibility = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible) schedule();
      else { cancelAnimationFrame(frame); frame = 0; }
    });
    visibility.observe(element);
    update();
    return () => { unsubscribe(); unsubscribeColors?.(); resize.disconnect(); visibility.disconnect(); cancelAnimationFrame(frame); };
  }, [nodeId, view, settings]);
  return <canvas ref={canvas} role="img" aria-label={title} className={`block w-full ${view.kind === "color" ? "h-14" : view.kind === "trigger" ? "h-10" : "h-36"}`} />;
}
