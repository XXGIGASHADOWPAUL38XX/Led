import { Handle, Position, useNodeId, useReactFlow, useUpdateNodeInternals } from "@xyflow/react";
import { useContext, useEffect } from "react";
import type { Endpoint } from "@/api/protocol";
import { terminalKey } from "./terminal-compatibility";
import { WorkspaceContext } from "./workspace-context";

// The React Flow handle fills the terminal dot; the dot keeps its own placement and look.
const handleStyle = {
  inset: 0,
  width: "100%",
  height: "100%",
  minWidth: 0,
  minHeight: 0,
  transform: "none",
  background: "transparent",
  border: 0,
  borderRadius: "9999px",
};

export function Terminal({
  endpoint,
  direction,
  className = "",
}: {
  endpoint?: Endpoint;
  direction: "input" | "output";
  className?: string;
}) {
  const workspace = useContext(WorkspaceContext);
  const nodeId = useNodeId();
  // Terminals outside a canvas node (e.g. the add-node dialog) are display-only.
  const connectable = Boolean(endpoint && workspace && nodeId === endpoint.nodeId);
  const key = endpoint ? terminalKey(endpoint, direction) : undefined;
  // React Flow measures handles with their node; a handle mounting after that measure is re-measured or its wires
  // never draw. Before the first measure it is left alone, so the initial fitView still sees every node.
  const flow = useReactFlow();
  const updateNodeInternals = useUpdateNodeInternals();
  useEffect(() => {
    if (connectable && flow.getInternalNode(nodeId!)?.measured.width) updateNodeInternals(nodeId!);
  }, [connectable, nodeId, key, flow, updateNodeInternals]);
  const linked = Boolean(key && workspace?.linked.has(key));
  const compatible =
    key && workspace?.compatible && workspace.origin !== key ? workspace.compatible.has(key) : undefined;
  const label = `${endpoint ? `${endpoint.nodeId}.${endpoint.element} ` : ""}${direction}${linked ? " · connected" : ""}`;
  return (
    <span
      data-terminal={key}
      data-linked={linked || undefined}
      data-compatible={compatible}
      role="button"
      tabIndex={connectable ? 0 : -1}
      aria-label={label}
      title={`${label}${compatible ? " · Compatible connection" : ""} · Drag to connect · Click to select its wires · Delete to disconnect`}
      onKeyDown={(event) => {
        if (connectable && (event.key === "Delete" || event.key === "Backspace")) {
          event.preventDefault();
          event.stopPropagation();
          workspace!.disconnect(key!);
        }
      }}
      className={`group/terminal z-10 inline-block h-3 w-3 shrink-0 cursor-crosshair touch-none rounded-full border-2 outline-none focus-visible:ring-2 focus-visible:ring-white/70 data-[compatible=false]:opacity-25 data-[compatible=true]:ring-4 data-[compatible=true]:ring-emerald-400/60 ${direction === "input" ? "border-sky-400 data-[linked]:bg-sky-400" : "border-violet-400 data-[linked]:bg-violet-400"} bg-card ${className}`}
    >
      <span aria-hidden="true" className="relative block h-full w-full">
        <span className="absolute -inset-2 rounded-full transition-colors group-focus/terminal:bg-violet-400/15 group-focus/terminal:ring-2 group-focus/terminal:ring-violet-300/60 hover:bg-violet-400/20" />
        {connectable && (
          <Handle
            id={endpoint!.element}
            type={direction === "output" ? "source" : "target"}
            position={direction === "output" ? Position.Right : Position.Left}
            style={handleStyle}
            onClick={(event) => {
              // Keep the click from also selecting the node, which Delete would then remove.
              event.stopPropagation();
              workspace!.selectPort(key!, event.ctrlKey || event.metaKey);
            }}
          />
        )}
      </span>
    </span>
  );
}
