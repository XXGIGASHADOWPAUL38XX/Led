import { test as base, expect, type Locator, type Page } from "@playwright/test";
import { BACKEND_PORT } from "../playwright.config";

type Graph = { nodes: unknown[]; connections: unknown[] };

/** The graph the backend starts with (see backend/api/server.py main()). */
export const defaultGraph: Graph = {
  nodes: [
    { id: "buffer-1", type: "Buffer", position: [0, 0], parameters: { length: 2048 } },
    { id: "amplitudes-1", type: "Amplitudes", position: [0, 0], parameters: {} },
  ],
  connections: [
    {
      id: "buffer-amplitudes",
      source: { nodeId: "buffer-1", element: "data" },
      target: { nodeId: "amplitudes-1", element: "buffer" },
    },
  ],
};

/** Load a graph straight through the backend HTTP API, independently of the UI under test. */
async function loadGraph(graph: Graph) {
  const response = await fetch(`http://127.0.0.1:${BACKEND_PORT}/api/v1/graph`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ graph }),
  });
  expect(response.ok, await response.text()).toBe(true);
}

export class Workspace {
  constructor(readonly page: Page) {}

  nodes = () => this.page.locator(".react-flow__node");
  edges = () => this.page.locator(".react-flow__edge");
  selectedNodes = () => this.page.locator(".react-flow__node.selected");
  selectedEdges = () => this.page.locator(".react-flow__edge.selected");
  node = (id: string) => this.page.locator(`.react-flow__node[data-id="${id}"]`);
  terminal = (nodeId: string, element: string, direction: "input" | "output") =>
    this.page.locator(`[data-terminal='${JSON.stringify([nodeId, element, direction])}']`);
  handle = (nodeId: string, element: string, direction: "input" | "output") =>
    this.terminal(nodeId, element, direction).locator(".react-flow__handle");

  async open() {
    await this.page.goto("/");
    await expect(this.nodes()).toHaveCount(2);
    // The default graph has no positions: wait for its automatic layout and the fitView that follows.
    await expect.poll(() => this.position("buffer-1")).not.toBe("translate(0px, 0px)");
    await this.settled();
  }
  /** Wait until the viewport stops moving, so pointer coordinates still hit what was measured. */
  async settled() {
    const viewport = () =>
      this.page.locator(".react-flow__viewport").evaluate((node) => (node as HTMLElement).style.transform);
    let previous = "";
    await expect
      .poll(
        async () => {
          const current = await viewport();
          const stable = current === previous;
          previous = current;
          return stable;
        },
        { intervals: [100] },
      )
      .toBe(true);
  }
  position(id: string) {
    return this.node(id).evaluate((node) => (node as HTMLElement).style.transform);
  }
  async center(locator: Locator) {
    const box = (await locator.boundingBox())!;
    return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  }
  /** Press, move in small steps, and leave the pointer down so callers can inspect the drag. */
  async press(from: { x: number; y: number }, to: { x: number; y: number }, steps = 12) {
    await this.page.mouse.move(from.x, from.y);
    await this.page.mouse.down();
    await this.page.mouse.move(to.x, to.y, { steps });
  }
  async drag(from: { x: number; y: number }, to: { x: number; y: number }, steps = 12) {
    await this.press(from, to, steps);
    await this.page.mouse.up();
  }
  async undo() {
    await this.page.getByRole("button", { name: "Undo ⌘Z" }).click();
  }
}

/** Each test starts from the default graph and fails on any browser error. */
export const test = base.extend<{ workspace: Workspace }>({
  workspace: async ({ page }, use) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(message.text());
    });
    await loadGraph(defaultGraph);
    const workspace = new Workspace(page);
    await workspace.open();
    await use(workspace);
    expect(errors, "browser errors").toEqual([]);
  },
});
export { expect };
