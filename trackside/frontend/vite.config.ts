import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.ico", "apple-touch-icon.png", "mask-icon.svg"],
      manifest: {
        name: "Trackside",
        short_name: "Trackside",
        description: "Motorsport Driver Safety & Performance Telemetry Console",
        theme_color: "#0A0E13",
        background_color: "#0A0E13",
        display: "standalone",
        orientation: "any",
        icons: [
          {
            src: "/images/icon-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "/images/icon-512.png",
            sizes: "512x512",
            type: "image/png",
          },
        ],
      },
      workbox: {
        // Private data must never be kept by the service worker: its cache is shared by every account
        // that uses this browser, so a cached /api/auth/me/ could show the wrong person's dashboard.
        // So no API route is cached at all, and navigations never fall back to the page for /api or /ws.
        navigateFallbackDenylist: [/^\/demo\//, /^\/api\//, /^\/ws\//],
        runtimeCaching: [],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "http://localhost:8000",
        ws: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: [],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
