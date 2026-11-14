import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  // The proxy keeps development same-origin without exposing any runtime key.
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "three", test: /node_modules\/(three|@react-three)/ },
          ],
        },
      },
    },
  },
});
