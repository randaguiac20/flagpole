/// <reference types="node" />
// Vite config. Spec: 002-flagpole-web (plan §Technical Context).
// Ports come from the project table (.env.example / docs/ports.md); the API is same-origin under /api
// in every environment (proxy here, ingress path in the cluster), so the app needs no CORS.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const WEB_PORT = Number(process.env.FLAGPOLE_WEB_PORT ?? 18010);
const API_PORT = Number(process.env.FLAGPOLE_API_PORT ?? 18000);

// `vite preview` gets the same proxy as `vite dev`; without it every /api call 404s against the
// preview server and the app looks broken for reasons that have nothing to do with the build.
const proxy = {
  "/api": {
    target: `http://127.0.0.1:${API_PORT}`,
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  server: { port: WEB_PORT, strictPort: true, proxy },
  preview: { port: WEB_PORT, strictPort: true, proxy },
});
