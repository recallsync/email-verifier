import path from "path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:5050",
      "/verify-email": "http://localhost:5050",
      "/find-email": "http://localhost:5050",
      "/health": "http://localhost:5050",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
