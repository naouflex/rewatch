import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The landing site is served as a SPA by nginx in production (see Dockerfile).
// In dev we also need historyApiFallback so deep links like /help/queries work.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
