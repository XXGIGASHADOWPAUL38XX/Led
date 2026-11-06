import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useBackend } from "@/api/backend-context";
import { useBackendStatus, useGeneration, useGraph } from "@/api/hooks";
import { JevPreview } from "./jev-preview";

export function JevControls() {
  const backend = useBackend();
  const [prompt, setPrompt] = useState("");
  const [pending, setPending] = useState(false);
  const generation = useGeneration();
  const status = useBackendStatus();
  const snapshot = useGraph();
  const running = generation.status === "running";
  const connected = status.connection === "connected";
  const disabled = !connected || running || pending || !prompt.trim();

  async function command(start: () => Promise<unknown>) {
    setPending(true);
    try {
      await start();
    } finally {
      setPending(false);
    }
  }
  const generate = (mode: "generate" | "edit") => command(() => backend.jev.generate(prompt, mode));

  return (
    <details className="rounded-xl border border-violet-400/20 bg-violet-400/5 p-3" open={running || undefined}>
      <summary className="cursor-pointer text-xs font-medium text-violet-200">
        Jev{running ? ` · ${generation.mode === "edit" ? "Editing" : "Generating"} · ${generation.nodes} nodes` : ""}
      </summary>
      <form
        className="mt-3 space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          void generate("generate");
        }}
      >
        <label className="block text-xs text-zinc-400">
          Describe your lighting
          <Textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={running || pending}
            maxLength={16000}
            rows={2}
            placeholder="Deep violet techno lights with sharp bass pulses and gentle high-frequency flashes…"
            className="mt-2 block bg-zinc-950/70 p-3 text-sm"
          />
        </label>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={disabled}>
            Generate graph
          </Button>
          <Button
            variant="outline"
            disabled={disabled || !snapshot?.graph.nodes.length}
            onClick={() => {
              void generate("edit");
            }}
          >
            Edit current graph
          </Button>
          {running && (
            <Button
              variant="outline"
              disabled={!connected || pending}
              onClick={() => {
                void command(() => backend.jev.cancel());
              }}
            >
              Cancel
            </Button>
          )}
          <p role="status" className={`text-xs ${generation.status === "error" ? "text-rose-300" : "text-zinc-400"}`}>
            {generation.message || "Loads the completed graph. Undo restores your previous graph."}
          </p>
        </div>
      </form>
      {running && <JevPreview />}
    </details>
  );
}
