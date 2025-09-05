// vite.config.js (example)
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default {
  server: {
    proxy: {
      '/feed': { target: 'http://localhost:8000', changeOrigin: true, ws: false },
      '/preferences': { target: 'http://localhost:8000', changeOrigin: true, ws: false },
      '^/ws': { target: 'ws://localhost:8000', ws: true },
    }
  },

  plugins: [react()],
};