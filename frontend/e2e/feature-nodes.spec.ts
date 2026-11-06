import { BACKEND_PORT } from "../playwright.config";
import { expect, test } from "./fixtures";

const api = `http://127.0.0.1:${BACKEND_PORT}/api/v1`;

test("Blend and Clustering forms work in the add-node dialog outside the canvas", async ({ workspace, page }) => {
  for (const title of ["Blend", "Clustering"]) {
    await page.getByRole("button", { name: "Add node ⌃A" }).click();
    await page.getByLabel("Search nodes").fill(title);
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: title })).toBeVisible();
    await dialog
      .getByRole("button", { name: title === "Blend" ? "Add input · or drop a wire" : "Add parameter", exact: true })
      .click();
    await expect(
      dialog.getByRole("button", { name: title === "Blend" ? "Remove input 1" : "Remove parameter 1", exact: true }),
    ).toBeVisible();
    await dialog.getByRole("button", { name: "Create node" }).click();
    await expect(dialog).toBeHidden();
    await expect(workspace.node(title)).toBeVisible();
  }
});

test("new node controls and stream views consume the backend catalog", async ({ workspace, page }) => {
  const types = ["ArrayReshaper", "Blend", "Clustering", "Correlate", "CosineAngle", "DimensionalFlattening"];
  const loaded = await page.request.put(`${api}/graph`, {
    data: {
      graph: {
        nodes: types.map((type, index) => ({ id: type, type, position: [index * 400, 0], parameters: {} })),
        connections: [],
      },
    },
  });
  expect(loaded.ok(), await loaded.text()).toBe(true);
  await expect(workspace.nodes()).toHaveCount(types.length);
  await expect(workspace.node("CosineAngle").getByRole("img", { name: "Direction", exact: true })).toBeAttached();
  await expect(workspace.node("Clustering").getByRole("img", { name: "Clustering", exact: true })).toBeAttached();
  const nmf = workspace.node("DimensionalFlattening");
  await expect(nmf.getByRole("img", { name: "Feature space · NMF" })).toBeAttached();
  await nmf.getByRole("button", { name: "recalibrate", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  const reshaper = workspace.node("ArrayReshaper");
  await reshaper.getByRole("switch", { name: "Slice", exact: true }).click();
  await expect(reshaper.getByRole("spinbutton", { name: "Values minimum", exact: true })).toBeAttached();
  await reshaper.getByRole("switch", { name: "Slice", exact: true }).click();
  await expect(reshaper.getByRole("spinbutton", { name: "Values minimum", exact: true })).toHaveCount(0);
});
