import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "NEXT_PUBLIC_");
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    // Preserve the existing WebSocket client and its environment variable.
    define: { "process.env.NEXT_PUBLIC_BACKEND_URL": JSON.stringify(env.NEXT_PUBLIC_BACKEND_URL) ?? "undefined" },
    server: { host: "127.0.0.1", port: 3000, strictPort: true },
    preview: { host: "127.0.0.1", port: 3000, strictPort: true },
  };
});
