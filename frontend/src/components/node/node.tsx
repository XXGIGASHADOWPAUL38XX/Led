"use client";

import { type ReactNode, useContext, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Terminal, TerminalContext } from "../workspace/terminal";

export type NodeProps = {
  children?: ReactNode;
  initialPosition?: { x: number; y: number };
  onPositionCommit?: (position: { x: number; y: number }) => void;
  id: string;
  title: string;
  description?: string;
  inputs?: string[];
  outputs?: string[];
  absolute?: boolean;
};

export function Node({ id, title, description, inputs = [], outputs = [], children, initialPosition, onPositionCommit, absolute = false }: NodeProps) {
  const [position, setPosition] = useState(initialPosition ?? { x: 0, y: 0 });
  const initialX = initialPosition?.x ?? 0, initialY = initialPosition?.y ?? 0;
  useEffect(() => { setPosition({ x: initialX, y: initialY }); }, [initialX, initialY]);
  const drag = useRef({ x: 0, y: 0 });
  const article = useRef<HTMLElement>(null);
  const workspace = useContext(TerminalContext);
  const invalidate = workspace?.invalidate;
  const zoom = workspace?.zoom ?? 1;
  useLayoutEffect(() => { invalidate?.(); }, [position, invalidate]);
  useLayoutEffect(() => {
    if (!invalidate) return;
    const observer = new ResizeObserver(invalidate);
    observer.observe(article.current!);
    return () => observer.disconnect();
  }, [invalidate]);

  return (
    <article ref={article} aria-label={`${title} node`} data-node-id={id}
      style={{ transform: `translate(${position.x}px, ${position.y}px)` }}
      className={`${absolute ? "absolute left-0 top-0" : "relative"} w-72 rounded-xl border border-violet-400/50 bg-[#1c1d26] shadow-2xl shadow-black/40`}>
      <button type="button" aria-label={`Drag ${title}`} className="flex w-full touch-none select-none items-center gap-3 rounded-t-xl border-b border-white/10 px-4 py-3 text-left active:cursor-grabbing focus-visible:outline-2 focus-visible:outline-violet-400"
        onPointerDown={(event) => {
          event.currentTarget.setPointerCapture(event.pointerId);
          drag.current = { x: event.clientX / zoom - position.x, y: event.clientY / zoom - position.y };
        }}
        onPointerMove={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            setPosition({ x: event.clientX / zoom - drag.current.x, y: event.clientY / zoom - drag.current.y });
          }
        }}
        onPointerUp={(event) => { event.currentTarget.releasePointerCapture(event.pointerId); onPositionCommit?.(position); }}
        onKeyDown={(event) => {
          const delta = { ArrowLeft: [-10, 0], ArrowRight: [10, 0], ArrowUp: [0, -10], ArrowDown: [0, 10] }[event.key];
          if (delta) {
            event.preventDefault();
            const next = { x: position.x + delta[0], y: position.y + delta[1] };
            setPosition(next);
            onPositionCommit?.(next);
          }
        }}>
        <span className="h-2 w-2 rounded-full bg-violet-400" />
        <span className="flex-1 text-sm font-semibold">{title}</span>
        <span aria-hidden="true" className="text-zinc-500">⠿</span>
      </button>
      {description && <p className="px-4 py-4 text-xs leading-5 text-zinc-400">{description}</p>}
      {children && <div className="space-y-2 px-3 pb-4">{children}</div>}
      <div className="flex justify-between gap-4 pb-4 text-xs text-zinc-300">
        <div className="space-y-3">{inputs.map((name) => <div key={name} className="flex items-center gap-2"><Terminal endpoint={{ nodeId: id, element: name }} direction="input" className="-ml-1.5" />{name}</div>)}</div>
        <div className="space-y-3">{outputs.map((name) => <div key={name} className="flex items-center justify-end gap-2">{name}<Terminal endpoint={{ nodeId: id, element: name }} direction="output" className="-mr-1.5" /></div>)}</div>
      </div>
    </article>
  );
}
