import { LiveWorkspace } from "@/features/graph/live-workspace";

export default function App() {
  return (
    <main className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-border px-6 py-5">
        <div className="flex items-center gap-4">
          <span className="rounded-lg bg-violet-400/15 px-3 py-2 text-sm font-bold tracking-widest text-violet-300">
            LED
          </span>
          <h1 className="text-sm font-medium">Node workspace</h1>
        </div>
        <span className="text-xs text-muted-foreground">Python ↔ MessagePack ↔ WebSocket</span>
      </header>
      <LiveWorkspace />
      <footer className="border-t border-border px-6 py-4 text-xs text-muted-foreground">
        Drag the node header to move it · Focus the header and use arrow keys
      </footer>
    </main>
  );
}
