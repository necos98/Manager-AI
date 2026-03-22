import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendProxy = {
  "/api": {
    target: process.env.BACKEND_URL || "http://localhost:8000",
    changeOrigin: true,
    ws: true,
  },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: backendProxy,
  },
  preview: {
    host: true,
    proxy: backendProxy,
  },
});
