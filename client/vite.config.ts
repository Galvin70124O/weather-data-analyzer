/// <reference types="vitest/config" />
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the FastAPI server runs on :8000. Proxying /api keeps everything on ONE origin,
// so the httpOnly session cookie just works (no CORS, same as production on Render).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  build: {
    rollupOptions: {
      output: {
        // Long-lived vendor chunks: they change less often than the app, so browsers keep them
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/[\/](react|react-dom|react-router|react-router-dom|scheduler)[\/]/.test(id)) return "react";
          if (/[\/](@radix-ui|cmdk)[\/]/.test(id)) return "ui";
          if (/[\/](framer-motion|motion-dom|motion-utils)[\/]/.test(id)) return "motion";
          if (/[\/]@tanstack[\/]/.test(id)) return "query";
          return undefined;     // the rest (Recharts with its d3 helpers, icons) follows its lazy importers
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
