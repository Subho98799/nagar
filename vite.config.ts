import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [reactRouter(), tsconfigPaths()],
  server: {
    host: "127.0.0.1", // Explicitly bind to IPv4 localhost
    port: 5173,
  },
});
