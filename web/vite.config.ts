import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Polling is enabled only inside the dev container (see docker-compose.override.yml):
// Windows-host bind mounts do not deliver filesystem events to Linux containers.
const usePolling = process.env.DEV_WATCH_POLLING === "true";
const pollIntervalMs = Number(process.env.DEV_WATCH_POLL_MS ?? 1000);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    watch: usePolling
      ? {
          usePolling: true,
          interval: pollIntervalMs,
          binaryInterval: pollIntervalMs * 3,
          ignored: ["**/dist/**", "**/coverage/**"],
        }
      : undefined,
  },
});
