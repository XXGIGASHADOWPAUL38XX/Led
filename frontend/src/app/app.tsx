import { LiveWorkspace } from "@/features/graph/live-workspace";

export default function App() {
  return (
    <main className="flex min-h-screen flex-col">
      <h1 className="sr-only">Node workspace</h1>
      <LiveWorkspace />
      <footer className="border-t border-border px-6 py-4 text-xs text-muted-foreground">
        Drag the node header to move it · Focus the header and use arrow keys
      </footer>
    </main>
  );
}
