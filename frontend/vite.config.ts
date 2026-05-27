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
    configure: (proxy: any) => {
      proxy.on("error", (err: NodeJS.ErrnoException, _req: unknown, _res: unknown) => {
        // ECONNRESET is expected when the backend closes a WebSocket
        // (terminal killed, process exited, server restart).
        // ECONNREFUSED is expected during backend restarts.
        // Don't pollute the console with these harmless events.
        if (err.code === "ECONNRESET" || err.code === "ECONNREFUSED") return;
        console.warn("[vite proxy]", err.message);
      });
    },
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
