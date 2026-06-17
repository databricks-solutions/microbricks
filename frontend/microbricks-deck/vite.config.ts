import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { TanStackRouterVite } from "@tanstack/router-plugin/vite";
import path from "path";

export default defineConfig(({ command }) => ({
  plugins: [
    TanStackRouterVite({
      target: "react",
      autoCodeSplitting: true,
      routesDirectory: "routes",
      generatedRouteTree: "types/routeTree.gen.ts",
    }),
    react(),
    tailwindcss(),
  ],
  root: "src/microbricks_deck/ui",
  publicDir: "public",
  base: command === "build" ? "/microbricks/deck/" : "/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src/microbricks_deck/ui"),
    },
  },
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
  },
}));
