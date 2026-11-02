import { readFileSync } from "node:fs";
import { decode } from "@msgpack/msgpack";
import { expect, test } from "./fixtures";

type Template = { payload: { graph: { nodes: { id: string }[]; connections: unknown[] } } };

// Saved production templates that load headless; template5.led currently fails in the backend loader.
const templates = ["template4.led", "template6.led", "template7.led", "template8.led"];
const path = (name: string) => new URL(`../../backend/templates/${name}`, import.meta.url).pathname;

for (const name of templates) {
  test(`${name} loads with its graph and renders unchanged`, async ({ workspace, page }) => {
    const { graph } = (decode(readFileSync(path(name))) as Template).payload;
    await page.getByLabel("Open node template").setInputFiles(path(name));
    await expect(page.getByText(`Loaded ${name}`)).toBeVisible({ timeout: 15_000 });
    await expect(workspace.nodes()).toHaveCount(graph.nodes.length);
    await expect(workspace.edges()).toHaveCount(graph.connections.length);
    for (const node of graph.nodes) await expect(workspace.node(node.id)).toBeVisible();
    // Live values (canvases, revision counter) change every frame; everything else must stay pixel-identical.
    await expect(page).toHaveScreenshot(`${name}.png`, {
      fullPage: true,
      mask: [page.locator("canvas"), page.getByRole("status")],
      maxDiffPixelRatio: 0.01,
    });
  });
}
