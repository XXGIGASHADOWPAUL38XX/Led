"use client";

import { useRef, useState } from "react";
import { backend } from "@/lib/backend/store";
import { useBackendStatus } from "@/lib/backend/hooks";
import { MAX_TEMPLATE_BYTES } from "@/lib/backend/template";
import { saveFile } from "@/lib/files/save-file";

export function TemplateControls() {
  const status = useBackendStatus();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"save" | "load" | "init" | null>(null);
  const [filename, setFilename] = useState("lighting-template.led");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const disabled = busy !== null || status.connection !== "connected";

  async function save() {
    setBusy("save"); setError(""); setMessage("");
    try {
      const name = await saveFile(filename, () => backend.exportTemplate());
      setFilename(name);
      setMessage(`Saved ${name}`);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(reason instanceof Error ? reason.message : "Could not save template.");
    }
    finally { setBusy(null); }
  }
  async function load(file?: File) {
    setBusy(file ? "load" : "init"); setError(""); setMessage("");
    try {
      let bytes: ArrayBuffer;
      const name = file?.name ?? "init_template.led";
      if (file) {
        if (file.size > MAX_TEMPLATE_BYTES) throw Error("Template exceeds 64 MB.");
        bytes = await file.arrayBuffer();
      } else {
        const response = await fetch("/templates/init_template.led");
        if (!response.ok) throw Error("Could not load init_template.led.");
        bytes = await response.arrayBuffer();
      }
      await backend.importTemplate(bytes);
      setFilename(name.endsWith(".led") ? name : "lighting-template.led");
      setMessage(`Loaded ${name}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load template."); }
    finally { setBusy(null); }
  }
  return <div className="space-y-1 text-xs">
    <div className="flex flex-wrap gap-2">
      <button type="button" disabled={disabled} onClick={() => { void load(); }} className="rounded border border-white/10 px-3 py-2 text-zinc-300 hover:bg-white/5 disabled:opacity-40">{busy === "init" ? "Loading…" : "init_template"}</button>
      <button type="button" disabled={disabled} onClick={() => { void save(); }} className="rounded border border-violet-400/25 bg-violet-400/10 px-3 py-2 text-violet-200 hover:bg-violet-400/20 disabled:opacity-40">{busy === "save" ? "Saving…" : "Save template"}</button>
      <button type="button" disabled={disabled} onClick={() => input.current?.click()} className="rounded border border-white/10 px-3 py-2 text-zinc-300 hover:bg-white/5 disabled:opacity-40">{busy === "load" ? "Loading…" : "Load template"}</button>
      <input ref={input} type="file" accept=".led" aria-label="Open node template" className="hidden" onChange={(event) => {
        const file = event.currentTarget.files?.[0];
        event.currentTarget.value = "";
        if (file) void load(file);
      }} />
    </div>
    {message && <p role="status" className="text-zinc-400">{message}</p>}
    {error && <p role="alert" className="text-rose-300">{error}</p>}
  </div>;
}
