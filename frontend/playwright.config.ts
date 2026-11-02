import { defineConfig, devices } from "@playwright/test";

// End-to-end runs use their own backend and dev server ports, so they never touch a running dev session.
export const BACKEND_PORT = 8001;
const FRONTEND_PORT = 3001;
// Resolved from the repository root, where the backend runs.
const python = process.env.E2E_PYTHON ?? ".venv/bin/python";

export default defineConfig({
  testDir: "e2e",
  // Every test shares one backend graph, so tests run one at a time.
  workers: 1,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
    viewport: { width: 1600, height: 1100 },
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 1100 } } }],
  webServer: [
    {
      command: `${python} node.py --port ${BACKEND_PORT}`,
      cwd: "..",
      port: BACKEND_PORT,
      reuseExistingServer: false,
    },
    {
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      port: FRONTEND_PORT,
      env: { VITE_BACKEND_URL: `ws://127.0.0.1:${BACKEND_PORT}/ws` },
      reuseExistingServer: false,
    },
  ],
});
