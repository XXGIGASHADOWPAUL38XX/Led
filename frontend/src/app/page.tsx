import { LiveWorkspace } from "@/components/workspace/live-workspace";
import { EditorsPreview, ParametersPreview } from "@/components/previews/editors-preview";
import { AnalysisPreview } from "@/components/previews/analysis-preview";
import { ControlsPreview } from "@/components/previews/controls-preview";
import { PlaylistPreview } from "@/components/previews/playlist-preview";
import { AmplitudesPreview } from "@/components/previews/amplitudes-preview";
import { BufferPreview } from "@/components/previews/buffer-preview";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-5">
        <div className="flex items-center gap-4"><span className="rounded-lg bg-violet-400/15 px-3 py-2 text-sm font-bold tracking-widest text-violet-300">LED</span><h1 className="text-sm font-medium">Node workspace</h1></div>
        <span className="text-xs text-zinc-500">Python ↔ MessagePack ↔ WebSocket</span>
      </header>
      <LiveWorkspace />
      <details className="p-4"><summary className="cursor-pointer text-xs text-zinc-400">Component previews</summary>
      <section aria-label="Node canvas" className="node-canvas relative flex min-h-[75vh] flex-1 flex-wrap items-center justify-center gap-12 overflow-hidden p-8">
        <PlaylistPreview />
        <BufferPreview />
        <AmplitudesPreview />
        <ControlsPreview />
        <ParametersPreview />
        <EditorsPreview />
        <AnalysisPreview />
      </section>
      </details>
      <footer className="border-t border-white/10 px-6 py-4 text-xs text-zinc-500">Drag the node header to move it · Focus the header and use arrow keys</footer>
    </main>
  );
}
