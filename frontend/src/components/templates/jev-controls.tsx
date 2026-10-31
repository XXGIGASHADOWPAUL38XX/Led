import { useState } from "react";
import { backend } from "@/lib/backend/store";
import { useBackendStatus, useGeneration, useGraph } from "@/lib/backend/hooks";
import { JevPreview } from "./jev-preview";

export function JevControls() {
  const [prompt, setPrompt] = useState("");
  const [pending, setPending] = useState(false);
  const generation = useGeneration();
  const status = useBackendStatus();
  const snapshot = useGraph();
  const running = generation.status === "running";
  const connected = status.connection === "connected";
  const disabled = !connected || running || pending || !prompt.trim();

  async function command(type: string, mode: "generate" | "edit" = "generate") {
    setPending(true);
    try { await backend.command(type, type === "jev.generate" ? { prompt, mode } : {}); }
    finally { setPending(false); }
  }

  return <details className="rounded-xl border border-violet-400/20 bg-violet-400/5 p-3" open={running || undefined}>
    <summary className="cursor-pointer text-xs font-medium text-violet-200">Jev{running ? ` · ${generation.mode === "edit" ? "Editing" : "Generating"} · ${generation.nodes} nodes` : ""}</summary>
    <form className="mt-3 space-y-3" onSubmit={(event) => { event.preventDefault(); void command("jev.generate"); }}>
      <label className="block text-xs text-zinc-400">Describe your lighting
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} disabled={running || pending} maxLength={16000} rows={2}
          placeholder="Deep violet techno lights with sharp bass pulses and gentle high-frequency flashes…"
          className="mt-2 block w-full resize-y rounded-lg border border-white/10 bg-zinc-950/70 p-3 text-sm text-zinc-200 outline-none focus:border-violet-400/60 disabled:opacity-50" />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={disabled}
          className="rounded-lg bg-violet-400/20 px-3 py-2 text-xs text-violet-200 disabled:opacity-40">Generate graph</button>
        <button type="button" disabled={disabled || !snapshot?.graph.nodes.length} onClick={() => { void command("jev.generate", "edit"); }}
          className="rounded-lg border border-violet-400/30 px-3 py-2 text-xs text-violet-200 disabled:opacity-40">Edit current graph</button>
        {running && <button type="button" disabled={!connected || pending} onClick={() => { void command("jev.cancel"); }}
          className="rounded-lg border border-white/10 px-3 py-2 text-xs text-zinc-300 disabled:opacity-40">Cancel</button>}
        <p role="status" className={`text-xs ${generation.status === "error" ? "text-rose-300" : "text-zinc-400"}`}>
          {generation.message || "Loads the completed graph. Undo restores your previous graph."}
        </p>
      </div>
    </form>
    {running && <JevPreview />}
  </details>;
}
