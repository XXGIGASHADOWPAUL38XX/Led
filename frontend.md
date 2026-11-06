# Frontend implementation practices

Reference comparison: `a0d4f9a1c89164d91c99fd6402fb5619c5155020` → **remote `feat/web`**, fetched as `origin/feat/web` at `63392ac531e7776674a450654ad99c5e6588d36f`.

Source: [remote frontend at the reviewed commit](https://github.com/XXGIGASHADOWPAUL38XX/Led/tree/63392ac531e7776674a450654ad99c5e6588d36f/frontend). The comparison changes 239 frontend files, including moves, generated types, dependency files, and browser snapshots.

Use the remote architecture below when integrating features. Paths refer to that reference commit; this document does not assert that the current checkout already implements them.

## Architecture and ownership

- **Organize by feature.** Move domain UI from the broad `components` tree into `src/features/{catalog,graph,nodes,streams,player,templates,generation}`. Keep transport/state in `src/api`, shared primitives in `src/components/ui`, and generic helpers in `src/lib`.
- **Keep node UI metadata with its backend implementation.** The previous frontend registry and individual node-definition files are replaced by a backend catalog. Python node classes supply their `ui`; generic frontend fields and views consume it. Add node-specific metadata at that source rather than creating a second frontend registry.
- **Generate shared contracts.** Derive node definitions, descriptors, graph types, and HTTP endpoints from `src/api/schema.d.ts`, generated from the backend OpenAPI schema. Use `npm run api:generate` and `npm run api:check` when the contract changes; do not hand-edit generated declarations.
- **Inject the backend store.** `BackendProvider` receives a `BackendStore`, starts/stops its connection with the provider lifecycle, and exposes it through `useBackend()`. Feature components obtain their dependencies from context. Required contexts fail clearly outside their providers.

Evidence: `src/main.tsx`, `src/api/backend-provider.tsx`, `src/features/nodes/definition.ts`, `src/features/catalog/use-catalog-query.ts`, `src/lib/react/use-required-context.ts`.

## Transport and synchronized state

- **Use typed HTTP methods for graph operations.** The remote moves graph edits, templates, playback, generation, and catalog reads to `openapi-fetch`. Retain binary MessagePack WebSockets for live events, arrays, element edits, and stream subscriptions. Put API behavior in the store/client layer.
- **Share array serialization across transports.** HTTP carries array envelopes with base64 data; WebSockets carry binary data. Both restore validated typed arrays and preserve dtype/shape. Distinguish revision-bearing server messages from outgoing commands and saved templates.
- **Wait for an operation's streamed effects.** HTTP responses expose `X-Revision`; store calls wait until the WebSocket state reaches that revision, or disconnects. Apply state before announcing its revision so callers can read their writes.
- **Apply graph deltas.** `graph.patch` updates changed nodes/connections while retaining untouched descriptors, streamed arrays, and optimistic edits. Check the patch base revision and request a fresh graph when it does not match.
- **Separate graph replacement from edits.** Full snapshots increment `graphEpoch`. Key the React Flow provider by that epoch to reset selection, viewport, and layout for a replaced graph. Install imported display settings with its snapshot before the first layout.
- **Send subscription deltas.** Track wanted streams versus the current session's subscribed set; send only `add`/`remove` differences through `streams.update`. Clear that mirror on disconnect and after a refused subscription.
- **Use query caching for request data.** Catalog and node-type prototypes use TanStack Query, explicit query keys, conditional fetching, and infinite stale time for stable metadata. Catalog fetching relies on browser ETag revalidation.

Evidence: `src/api/{client,protocol,store}.ts`, `src/features/catalog/use-catalog-query.ts`, `src/features/nodes/add-node-dialog.tsx`.

## Graph interactions

- **Compose React Flow.** Replace custom canvas selection, movement, viewport, and wire-drag machinery with React Flow nodes, edges, handles, and callbacks. Keep backend graph state authoritative while retaining local selection, measurements, and active drag state by ID.
- **Commit settled movement.** Batch final node positions into one graph operation; restore authoritative positions on refusal. Arrange from measured node sizes, and automatically arrange unpositioned graphs after measurement.
- **Protect editing interactions.** Restrict dragging to node headers, validate connection direction/shapes, exclude self-connections, and ignore workspace shortcuts while typing or inside dialogs. Delete acts on wire selections; node removal stays explicit.

Evidence: `src/features/graph/workspace-canvas.tsx`, `src/features/graph/terminal.tsx`, `src/features/graph/shortcuts.ts`, `src/features/graph/terminal-compatibility.ts`.

## Shared UI and accessibility

- **Style primitives once.** Compose the shared Button, IconButton, Input, Select, Slider, Switch, Dialog, and Tooltip components. ESLint prohibits direct Radix imports outside `components/ui`.
- **Centralize visual roles.** Use semantic theme tokens in `src/styles/index.css`, shared button variants, and the `cn` class helper. Use the shared icon library and named tooltips for icon actions.
- **Expose interaction state.** Preserve labels, visible focus, slider value semantics, associated validation errors, and loading/disabled states. Shared buttons show progress and prevent repeated activation while loading.
- **Protect dialog drafts.** Use the shared dialog's focus behavior; explicitly focus search and prevent accidental outside clicks from discarding a partially completed node form.

Evidence: `src/components/ui`, `src/features/nodes/elements`, `src/features/nodes/add-node-dialog.tsx`, `eslint.config.js`.

## Rendering and build discipline

- **Keep stream rendering outside React updates.** Preserve the existing renderer/component separation, per-array subscriptions, animation-frame scheduling, visibility-aware drawing, bounded history, device-pixel scaling, and effect cleanup. These practices already existed in the baseline and are retained in `src/features/streams`.
- **Split stable dependencies from application code.** Vite creates separate React, React Flow, and vendor chunks so dependency assets can remain cached across application deployments.
- **Use the configured quality checks.** Run relevant unit tests, type checking/build, ESLint, and Prettier checks. Keep React Hooks and refresh lint rules enabled; regenerate/check API types after backend schema changes.

Evidence: `src/features/streams/{stream-canvas.tsx,canvas-renderer.ts}`, `vite.config.ts`, `eslint.config.js`, `package.json`.

## Regression coverage

- Extend unit coverage for revision ordering, HTTP/WebSocket synchronization, graph patches/resync, subscription deltas, optimistic edits, serialization, template state, layout, and connection compatibility.
- Use Playwright for real graph interactions: selection, wiring/disconnection, movement persistence, clipboard/undo, zoom, node creation, dialogs, and menus.
- Keep browser tests isolated on dedicated backend/frontend ports, run shared-graph tests sequentially, and exercise the production bundle. Retain failure traces and mask changing canvases/status text in visual snapshots.

Evidence: `src/api/*.test.mjs`, `src/features/**/*.test.mjs`, `e2e`, `playwright.config.ts`.

Scope: this document describes changes and practices evidenced on remote `feat/web`, not local `feat/web` or `feat/web2`. Microtask subscription batching, scatter/angle/clustering views, per-axis range persistence, and comprehensive stale-socket event guards are not established by this remote comparison. This review inspected source and test definitions; it did not run the remote branch's checks.
