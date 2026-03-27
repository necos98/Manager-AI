import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import { defineConfig } from "vite";
import path from "path";

const backendProxy = {
  "/api": {
    target: process.env.BACKEND_URL || "http://localhost:8000",
    changeOrigin: true,
    ws: true,
  },
};

export default defineConfig({
  plugins: [TanStackRouterVite({ quoteStyle: "double" }), react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    proxy: backendProxy,
  },
  preview: {
    host: true,
    proxy: backendProxy,
  },
});
