import { expect, test } from "./fixtures";

test("renders the live backend graph", async ({ workspace }) => {
  await expect(workspace.nodes()).toHaveCount(2);
  await expect(workspace.edges()).toHaveCount(1);
});

test("clicking a terminal selects its wires; Delete disconnects and Undo restores", async ({ workspace, page }) => {
  // Connected input terminals sit over the wire's reconnect anchor; the click must still select the wire only.
  await workspace.handle("amplitudes-1", "buffer", "input").click();
  await expect(workspace.selectedEdges()).toHaveCount(1);
  await expect(workspace.selectedNodes()).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(workspace.selectedEdges()).toHaveCount(0);

  await workspace.handle("buffer-1", "data", "output").click();
  await expect(workspace.selectedEdges()).toHaveCount(1);
  await page.keyboard.press("Delete");
  await expect(workspace.edges()).toHaveCount(0);
  await expect(workspace.nodes()).toHaveCount(2);
  await workspace.undo();
  await expect(workspace.edges()).toHaveCount(1);
});

test("dragging from an output highlights compatible terminals and drops in the void create nothing", async ({
  workspace,
  page,
}) => {
  await workspace.press(await workspace.center(workspace.handle("amplitudes-1", "data", "output")), {
    x: 300,
    y: 1000,
  });
  await expect(workspace.terminal("buffer-1", "indata", "input")).toHaveAttribute("data-compatible", "true");
  await expect(workspace.terminal("amplitudes-1", "buffer", "input")).toHaveAttribute("data-compatible", "false");
  await expect(workspace.terminal("amplitudes-1", "data", "output")).not.toHaveAttribute("data-compatible");
  await page.mouse.up();
  await expect(workspace.terminal("buffer-1", "indata", "input")).not.toHaveAttribute("data-compatible");
  await expect(workspace.edges()).toHaveCount(1);
});

test("dragging a connected input into the void disconnects; output to input reconnects", async ({ workspace }) => {
  await workspace.drag(await workspace.center(workspace.handle("amplitudes-1", "buffer", "input")), {
    x: 300,
    y: 1000,
  });
  await expect(workspace.edges()).toHaveCount(0);
  await workspace.drag(
    await workspace.center(workspace.handle("buffer-1", "data", "output")),
    await workspace.center(workspace.handle("amplitudes-1", "buffer", "input")),
  );
  await expect(workspace.edges()).toHaveCount(1);
});

test("node moves by header drag and arrow keys persist in the backend", async ({ workspace, page }) => {
  const initial = await workspace.position("buffer-1");
  const header = await workspace.center(workspace.node("buffer-1").locator("header"));
  await workspace.drag(header, { x: header.x - 150, y: header.y + 60 });
  await expect.poll(() => workspace.position("buffer-1")).not.toBe(initial);
  const dragged = await workspace.position("buffer-1");
  await page.reload();
  await expect.poll(() => workspace.position("buffer-1")).toBe(dragged);

  await workspace.node("buffer-1").locator("header").click();
  await workspace.node("buffer-1").focus();
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => workspace.position("buffer-1")).not.toBe(dragged);
  const moved = await workspace.position("buffer-1");
  await page.reload();
  await expect.poll(() => workspace.position("buffer-1")).toBe(moved);
});

test("interactive content inside a node does not drag it", async ({ workspace }) => {
  const before = await workspace.position("amplitudes-1");
  const box = (await workspace.node("amplitudes-1").getByRole("slider").first().boundingBox())!;
  await workspace.drag({ x: box.x + 2, y: box.y + box.height / 2 }, { x: box.x + 60, y: box.y + box.height / 2 }, 6);
  expect(await workspace.position("amplitudes-1")).toBe(before);
});

test("box selection, copy/paste, Delete on a node selection and Undo", async ({ workspace, page }) => {
  const pane = (await page.locator(".react-flow__pane").boundingBox())!;
  await workspace.drag({ x: pane.x + 5, y: pane.y + 5 }, { x: pane.x + pane.width - 5, y: pane.y + pane.height - 5 });
  await expect(workspace.selectedNodes()).toHaveCount(2);

  await page.mouse.move(pane.x + pane.width / 2, pane.y + pane.height / 2);
  await page.keyboard.press("Control+c");
  await page.keyboard.press("Control+v");
  await expect(workspace.nodes()).toHaveCount(4);
  await expect(workspace.selectedNodes()).toHaveCount(2);

  // A node selection also selects the wires between its nodes; Delete must leave both untouched.
  await page.keyboard.press("Delete");
  await expect(workspace.nodes()).toHaveCount(4);
  await expect(workspace.edges()).toHaveCount(2);
  await workspace.undo();
  await expect(workspace.nodes()).toHaveCount(2);
});

test("zoom with buttons, Ctrl+wheel and Ctrl+0", async ({ workspace, page }) => {
  const zoom = page.getByRole("button", { name: "Reset zoom" });
  const initial = await zoom.textContent();
  await page.getByRole("button", { name: "Zoom in" }).click();
  await expect(zoom).not.toHaveText(initial!);
  const zoomedIn = await zoom.textContent();
  const pane = (await page.locator(".react-flow__pane").boundingBox())!;
  await page.mouse.move(pane.x + 200, pane.y + 200);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, 400);
  await page.keyboard.up("Control");
  await expect(zoom).not.toHaveText(zoomedIn!);
  await page.keyboard.press("Control+0");
  await expect(zoom).toHaveText("100%");
  await expect(workspace.nodes()).toHaveCount(2);
});

test("Arrange nodes lays the graph out through the backend", async ({ workspace, page }) => {
  // The default graph has no positions, so it is already laid out once on load.
  const arranged = await workspace.position("buffer-1");
  const header = await workspace.center(workspace.node("buffer-1").locator("header"));
  await workspace.drag(header, { x: header.x + 200, y: header.y + 200 });
  await expect.poll(() => workspace.position("buffer-1")).not.toBe(arranged);
  await page.getByRole("button", { name: "Arrange nodes" }).click();
  await expect.poll(() => workspace.position("buffer-1")).toBe(arranged);
});

test("add-node dialog renders a node's fields outside the canvas", async ({ workspace, page }) => {
  await expect(workspace.nodes()).toHaveCount(2);
  await page.getByRole("button", { name: "Add node ⌃A" }).click();
  await page.getByLabel("Search nodes").fill("smoothing");
  await page.keyboard.press("Enter");
  await expect(page.locator("dialog[open]")).toBeVisible();
  await page.keyboard.press("Escape");
});

test("init_template loads and unpositioned nodes are laid out automatically", async ({ workspace, page }) => {
  await page.getByRole("button", { name: "init_template" }).click();
  await expect(workspace.nodes()).toHaveCount(3);
  await expect(workspace.edges()).toHaveCount(4);
  await expect
    .poll(
      async () =>
        new Set(
          await workspace.nodes().evaluateAll((nodes) => nodes.map((node) => (node as HTMLElement).style.transform)),
        ).size,
    )
    .toBe(3);
});
